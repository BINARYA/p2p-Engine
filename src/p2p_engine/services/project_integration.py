from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from p2p_engine.core.mutation_preview import semantic_sha256, source_precondition
from p2p_engine.core.project_integration import (
    PROJECT_ACCESS_PROFILES,
    PROJECT_INTEGRATION_CONTRACT,
    PROJECT_INTEGRATION_SECTION_ID,
    STANDALONE_PROFILE,
    access_profile,
    current_integration_versions,
    integration_contract_major,
    managed_section_markers,
    require_supported_profile,
)
from p2p_engine.core.runtime_contract import (
    RUNTIME_SETUP_GUIDE_MARKER,
    P2PRuntimeRequirement,
    RuntimeContract,
)
from p2p_engine.foundation.files import read_yaml_mapping, yaml_dump
from p2p_engine.services.agent_instructions import AgentInstructionService
from p2p_engine.services.agent_templates import project_integration_guide
from p2p_engine.services.runtime_contract import (
    RUNTIME_CONTRACT_SCHEMA_VERSION,
    RuntimeContractService,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter

_P2P_WHOLE_FILE_MARKER = "Managed by P2P Engine."
_LEGACY_RUNTIME_SETUP_GUIDE_MARKER = (
    b"<!-- P2P: generated-runtime-setup schema=1 "
    b"source=.p2p/project/runtime.yml -->"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(access[_-]?token|refresh[_-]?token|api[_-]?key|password|private[_-]?key|"
    r"authorization\s*:\s*bearer)\s*[:=]\s*[^\s<]+"
)


@dataclass(frozen=True)
class IntegrationArtifactState:
    path: str
    state: str
    ownership: str
    section_id: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "state": self.state,
            "ownership": self.ownership,
            "section_id": self.section_id or None,
            "message": self.message,
        }


@dataclass(frozen=True)
class IntegrationOperationResult:
    operation: str
    status: str
    profile: str
    changed_paths: tuple[str, ...] = ()
    artifacts: tuple[IntegrationArtifactState, ...] = ()
    message: str = ""
    recovery_required: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_INTEGRATION_CONTRACT,
            "operation": self.operation,
            "status": self.status,
            "profile": self.profile,
            "changed_paths": list(self.changed_paths),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "message": self.message,
            "recovery_required": self.recovery_required,
        }


class ProjectIntegrationService:
    """Own regenerable project/agent artifacts without touching project memory."""

    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        agent_instructions: AgentInstructionService,
        runtime_contract: RuntimeContractService,
        failure_injector=None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.agent_instructions = agent_instructions
        self.runtime_contract = runtime_contract
        self.failure_injector = failure_injector

    def profile_matrix(self) -> list[dict[str, object]]:
        return [access_profile(profile).to_dict() for profile in PROJECT_ACCESS_PROFILES]

    def status(self) -> dict[str, object]:
        registry = self._registry()
        integration = registry.get("integration", {})
        if not isinstance(integration, dict):
            integration = {}
        recorded_contract = integration.get("contract_version")
        recorded_major = integration_contract_major(recorded_contract)
        current_major = integration_contract_major(PROJECT_INTEGRATION_CONTRACT)
        unsupported_newer = (
            recorded_major is not None
            and current_major is not None
            and recorded_major > current_major
        )
        profile_name = str(integration.get("access_profile") or STANDALONE_PROFILE)
        try:
            profile = access_profile(profile_name)
        except ValueError:
            profile = access_profile(STANDALONE_PROFILE)
        artifacts = self._artifact_states(integration)
        versions_stale = integration.get("versions") != current_integration_versions()
        if versions_stale:
            artifacts = tuple(
                IntegrationArtifactState(
                    path=item.path,
                    state="stale" if item.state == "current" else item.state,
                    ownership=item.ownership,
                    section_id=item.section_id,
                    message=(
                        "Artifact was generated under different compatibility dimensions."
                        if item.state == "current"
                        else item.message
                    ),
                )
                for item in artifacts
            )
        states = {item.state for item in artifacts}
        if unsupported_newer:
            state = "unsupported"
        elif not self.agent_instructions.path().exists() or not integration:
            state = "missing"
        elif states & {"conflicting", "user-modified"}:
            state = "conflicting"
        elif "missing" in states:
            state = "missing"
        elif versions_stale:
            state = "stale"
        elif states & {"stale"}:
            state = "stale"
        else:
            state = "current"
        return {
            "contract": PROJECT_INTEGRATION_CONTRACT,
            "state": state,
            "active_profile": profile_name,
            "profile": profile.to_dict(),
            "profiles": self.profile_matrix(),
            "versions": current_integration_versions(),
            "recorded_versions": integration.get("versions"),
            "recorded_contract": recorded_contract,
            "manifest_path": str(self.agent_instructions.path().relative_to(self.root)),
            "artifacts": [item.to_dict() for item in artifacts],
            "host_configuration_mutation_via_mcp": False,
            "backend_exposed": False,
            "mutation_performed": False,
        }

    def install(
        self,
        *,
        profile: str = STANDALONE_PROFILE,
        agent_target: str = "generic",
    ) -> IntegrationOperationResult:
        return self._apply_projection(
            operation="install",
            profile=profile,
            agent_target=agent_target,
        )

    def refresh(self, *, profile: str = STANDALONE_PROFILE) -> IntegrationOperationResult:
        return self._apply_projection(operation="refresh", profile=profile)

    def transition(self, *, profile: str) -> IntegrationOperationResult:
        return self._apply_projection(operation="profile", profile=profile)

    def remove(self) -> IntegrationOperationResult:
        registry = self._registry()
        integration = self._require_supported_manifest(registry)
        records = integration.get("artifacts", [])
        if not isinstance(records, list) or not records:
            return IntegrationOperationResult(
                operation="remove",
                status="no-change",
                profile=str(integration.get("access_profile") or STANDALONE_PROFILE),
                message="No managed integration artifacts are installed.",
            )
        states = self._artifact_states(integration)
        blockers = [
            item for item in states if item.state in {"conflicting", "user-modified"}
        ]
        if blockers:
            return IntegrationOperationResult(
                operation="remove",
                status="blocked",
                profile=str(integration.get("access_profile") or STANDALONE_PROFILE),
                artifacts=tuple(blockers),
                message="User-modified or conflicting managed content was preserved.",
            )
        candidates: dict[str, bytes | None] = {}
        for raw in records:
            if not isinstance(raw, dict):
                continue
            relative = self._safe_relative(str(raw.get("path") or ""))
            path = self.root / relative
            ownership = str(raw.get("kind") or "whole-file")
            if ownership == "managed-section" and path.exists():
                section = self._parse_section(path.read_bytes())
                if section is None:
                    continue
                candidates[relative.as_posix()] = section.before + section.after
            else:
                candidates[relative.as_posix()] = None
        candidates[self.agent_instructions.path().relative_to(self.root).as_posix()] = None
        return self._commit(
            operation="remove",
            profile=str(integration.get("access_profile") or STANDALONE_PROFILE),
            candidates=candidates,
            artifact_states=states,
        )

    def _apply_projection(
        self,
        *,
        operation: str,
        profile: str,
        agent_target: str | None = None,
    ) -> IntegrationOperationResult:
        selected_profile = require_supported_profile(profile)
        registry = self._registry()
        self._require_supported_manifest(registry, allow_missing=True)
        profiles = self._installed_agent_profiles(registry)
        if agent_target is not None:
            normalized_target = self.agent_instructions.normalize_profile(agent_target)
            profiles = sorted(
                set(profiles) | set(self.agent_instructions.expanded_profiles(normalized_target))
            )
        project_name = self.agent_instructions.project_name()
        interaction_style = (
            self.agent_instructions.interaction_style()
            if self.agent_instructions.interaction_style is not None
            else None
        )
        rendered, _policy_path = self.agent_instructions._managed_instruction_files(
            project_name,
            profiles,
            interaction_style,
        )
        rendered[Path("P2P-INTEGRATION.md")] = project_integration_guide(
            selected_profile.profile
        )
        rendered[Path("P2P-SETUP.md")] = self._render_setup_guide()

        ownership: dict[str, dict[str, object]] = {}
        candidates: dict[str, bytes | None] = {}
        blockers: list[IntegrationArtifactState] = []
        old_artifacts = self._artifact_records(registry)
        for relative, content in sorted(rendered.items(), key=lambda item: item[0].as_posix()):
            relative = self._safe_relative(relative.as_posix())
            path = self.root / relative
            expected = content.encode("utf-8")
            old_record = old_artifacts.get(relative.as_posix())
            if relative == Path("AGENTS.md") and path.exists() and not self._is_owned_whole(path):
                section_result = self._merge_managed_section(
                    path.read_bytes(),
                    selected_profile.profile,
                    recorded=old_record,
                )
                if isinstance(section_result, IntegrationArtifactState):
                    blockers.append(section_result)
                    continue
                candidate, section_bytes = section_result
                candidates[relative.as_posix()] = candidate
                ownership[relative.as_posix()] = {
                    "kind": "managed-section",
                    "section_id": PROJECT_INTEGRATION_SECTION_ID,
                    "sha256": hashlib.sha256(section_bytes).hexdigest(),
                }
                continue
            if path.exists() and not self._can_replace_whole(path, old_record, relative):
                blockers.append(
                    IntegrationArtifactState(
                        path=relative.as_posix(),
                        state="user-modified",
                        ownership="whole-file",
                        message="Existing content is not provably owned and unchanged by P2P Engine.",
                    )
                )
                continue
            candidates[relative.as_posix()] = expected
            ownership[relative.as_posix()] = {
                "kind": "whole-file",
                "sha256": hashlib.sha256(expected).hexdigest(),
            }
        if blockers:
            return IntegrationOperationResult(
                operation=operation,
                status="blocked",
                profile=selected_profile.profile,
                artifacts=tuple(blockers),
                message="Conflicting or user-owned content was preserved; no artifact was changed.",
            )

        candidate_by_path = {Path(path): value for path, value in candidates.items()}
        new_registry = self.agent_instructions.build_registry(
            profiles,
            candidate_contents=candidate_by_path,
            artifact_ownership=ownership,
        )
        integration = new_registry.get("integration")
        assert isinstance(integration, dict)
        integration["access_profile"] = selected_profile.profile
        integration["profile"] = selected_profile.to_dict()
        new_registry["integration"] = integration
        registry_relative = self.agent_instructions.path().relative_to(self.root).as_posix()
        candidates[registry_relative] = yaml_dump(new_registry).encode("utf-8")
        self._validate_candidates(candidates)
        return self._commit(
            operation=operation,
            profile=selected_profile.profile,
            candidates=candidates,
            artifact_states=tuple(self._candidate_states(candidates, ownership)),
        )

    def _commit(
        self,
        *,
        operation: str,
        profile: str,
        candidates: dict[str, bytes | None],
        artifact_states: tuple[IntegrationArtifactState, ...] | list[IntegrationArtifactState],
    ) -> IntegrationOperationResult:
        effective = {
            path: content
            for path, content in candidates.items()
            if self._current_bytes(path) != content
        }
        if not effective:
            return IntegrationOperationResult(
                operation=operation,
                status="no-change",
                profile=profile,
                artifacts=tuple(artifact_states),
                message="Integration projection is already in the requested state.",
            )
        allowed = tuple(
            sorted(path for path in effective if not path.startswith(".p2p/"))
        )
        token = semantic_sha256(
            {
                "contract": PROJECT_INTEGRATION_CONTRACT,
                "operation": operation,
                "profile": profile,
                "candidates": {
                    path: hashlib.sha256(content).hexdigest() if content is not None else None
                    for path, content in sorted(effective.items())
                },
            }
        )
        writer = AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
            allowed_project_targets=allowed,
            failure_injector=self.failure_injector,
        )
        result = writer.apply(
            operation_id=f"project-integration-{operation}",
            candidates=effective,
            sources=tuple(
                source_precondition(path, self._current_bytes(path))
                for path in sorted(effective)
            ),
            preview_token=token,
            actor="local-owner",
        )
        status = "applied" if result.status == "applied" else result.status
        return IntegrationOperationResult(
            operation=operation,
            status=status,
            profile=profile,
            changed_paths=tuple(result.changed_paths),
            artifacts=tuple(artifact_states),
            message=result.message,
            recovery_required=result.recovery_required,
        )

    def _artifact_states(self, integration: dict[str, object]) -> tuple[IntegrationArtifactState, ...]:
        records = integration.get("artifacts", [])
        if not isinstance(records, list):
            return (
                IntegrationArtifactState(
                    path=str(self.agent_instructions.path().relative_to(self.root)),
                    state="conflicting",
                    ownership="manifest",
                    message="Integration artifacts must be a list.",
                ),
            )
        states: list[IntegrationArtifactState] = []
        for raw in records:
            if not isinstance(raw, dict):
                continue
            relative = self._safe_relative(str(raw.get("path") or ""))
            path = self.root / relative
            ownership = str(raw.get("kind") or "whole-file")
            digest = str(raw.get("sha256") or "")
            if not path.exists():
                state = "missing"
                message = "Managed artifact is missing."
            elif ownership == "managed-section":
                try:
                    section = self._parse_section(path.read_bytes())
                except ValueError as exc:
                    section = None
                    state = "conflicting"
                    message = str(exc)
                else:
                    if section is None:
                        state = "missing"
                        message = "Managed section is missing."
                    elif hashlib.sha256(section.section).hexdigest() != digest:
                        state = "user-modified"
                        message = "Managed section content differs from its manifest digest."
                    else:
                        state = "current"
                        message = ""
            elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                state = "user-modified"
                message = "Whole-file content differs from its manifest digest."
            else:
                state = "current"
                message = ""
            states.append(
                IntegrationArtifactState(
                    path=relative.as_posix(),
                    state=state,
                    ownership=ownership,
                    section_id=str(raw.get("section_id") or ""),
                    message=message,
                )
            )
        return tuple(states)

    def _candidate_states(
        self,
        candidates: dict[str, bytes | None],
        ownership: dict[str, dict[str, object]],
    ) -> list[IntegrationArtifactState]:
        return [
            IntegrationArtifactState(
                path=path,
                state="managed" if content is not None else "removed",
                ownership=str(ownership.get(path, {}).get("kind") or "whole-file"),
                section_id=str(ownership.get(path, {}).get("section_id") or ""),
            )
            for path, content in sorted(candidates.items())
            if path != self.agent_instructions.path().relative_to(self.root).as_posix()
        ]

    def _installed_agent_profiles(self, registry: dict[str, object]) -> list[str]:
        adapters = registry.get("adapters", {})
        if not isinstance(adapters, dict):
            return ["generic"]
        installed = [
            str(adapter)
            for adapter, record in adapters.items()
            if isinstance(record, dict) and record.get("status") == "installed"
        ]
        return sorted(set(installed) | {"generic"})

    def _artifact_records(self, registry: dict[str, object]) -> dict[str, dict[str, object]]:
        records = {
            self._safe_relative(path).as_posix(): dict(record)
            for path, record in self.agent_instructions.registry_file_map(registry).items()
        }
        integration = registry.get("integration", {})
        if not isinstance(integration, dict):
            return records
        artifacts = integration.get("artifacts", [])
        if not isinstance(artifacts, list):
            return records
        records.update(
            {
                self._safe_relative(str(record.get("path"))).as_posix(): record
                for record in artifacts
                if isinstance(record, dict) and record.get("path")
            }
        )
        return records

    def _require_supported_manifest(
        self,
        registry: dict[str, object],
        *,
        allow_missing: bool = False,
    ) -> dict[str, object]:
        integration = registry.get("integration", {})
        if not isinstance(integration, dict) or not integration:
            if allow_missing:
                return {}
            return {}
        recorded = integration.get("contract_version")
        recorded_major = integration_contract_major(recorded)
        current_major = integration_contract_major(PROJECT_INTEGRATION_CONTRACT)
        if recorded_major is None:
            raise ValueError(
                "P2P_INTEGRATION_CONTRACT_INVALID: preserve the manifest and use a compatible runtime"
            )
        if current_major is not None and recorded_major > current_major:
            raise ValueError(
                "P2P_INTEGRATION_CONTRACT_UNSUPPORTED: a newer integration manifest was "
                "preserved without modification"
            )
        return integration

    def _registry(self) -> dict[str, object]:
        path = self.agent_instructions.path()
        if not path.exists():
            return {"schema_version": 2, "baseline_profile": "generic", "adapters": {}}
        return read_yaml_mapping(path, default={})

    def _render_setup_guide(self) -> str:
        status = self.runtime_contract.status()
        if status.requires and status.recommended:
            contract = RuntimeContract(
                schema_version=RUNTIME_CONTRACT_SCHEMA_VERSION,
                p2p=P2PRuntimeRequirement(
                    requires=status.requires,
                    recommended=status.recommended,
                ),
            )
            return self.runtime_contract.render_setup_guide(contract)
        return self.runtime_contract.render_setup_guide()

    def _can_replace_whole(
        self,
        path: Path,
        old_record: dict[str, object] | None,
        relative: Path,
    ) -> bool:
        content = path.read_bytes()
        if relative == Path("P2P-SETUP.md"):
            first_line = content.splitlines()[0] if content else b""
            return first_line in {
                RUNTIME_SETUP_GUIDE_MARKER.encode("utf-8"),
                _LEGACY_RUNTIME_SETUP_GUIDE_MARKER,
            }
        if self._is_owned_whole(path):
            if old_record is None:
                return True
            expected = str(old_record.get("sha256") or "")
            return not expected or hashlib.sha256(content).hexdigest() == expected
        if relative.as_posix().startswith(".p2p/") and old_record is not None:
            expected = str(old_record.get("sha256") or "")
            return bool(expected) and hashlib.sha256(content).hexdigest() == expected
        return False

    def _is_owned_whole(self, path: Path) -> bool:
        try:
            prefix = path.read_text(encoding="utf-8")[:2048]
        except (OSError, UnicodeDecodeError):
            return False
        return _P2P_WHOLE_FILE_MARKER in prefix

    def _merge_managed_section(
        self,
        current: bytes,
        profile: str,
        *,
        recorded: dict[str, object] | None,
    ) -> tuple[bytes, bytes] | IntegrationArtifactState:
        expected = self._profile_section(profile)
        try:
            section = self._parse_section(current)
        except ValueError as exc:
            return IntegrationArtifactState(
                path="AGENTS.md",
                state="conflicting",
                ownership="managed-section",
                section_id=PROJECT_INTEGRATION_SECTION_ID,
                message=str(exc),
            )
        if section is None:
            return current + expected, expected
        recorded_digest = str((recorded or {}).get("sha256") or "")
        if not recorded_digest or hashlib.sha256(section.section).hexdigest() != recorded_digest:
            return IntegrationArtifactState(
                path="AGENTS.md",
                state="user-modified",
                ownership="managed-section",
                section_id=PROJECT_INTEGRATION_SECTION_ID,
                message="Managed section differs from its recorded digest and was preserved.",
            )
        return section.before + expected + section.after, expected

    def _profile_section(self, profile: str) -> bytes:
        selected = require_supported_profile(profile)
        start, end = managed_section_markers(selected.profile)
        if selected.profile == STANDALONE_PROFILE:
            access_lines = [
                "- Active profile: `standalone`; the local project is authoritative.",
                "- Use the local CLI or MCP over `stdio` for supported reads and governed writes.",
                "- Offline reads and governed local mutations are supported.",
            ]
        else:
            access_lines = [
                "- Active profile: `linked-local`; WaveKit is authoritative.",
                "- Local CLI and MCP over `stdio` may read the local replica as potentially stale.",
                "- Governed local mutations are blocked; never treat offline state as authoritative.",
                "- Use `p2p project transfer status|recover` for an interrupted handoff.",
            ]
        text = "\n".join(
            [
                start,
                "",
                "## P2P Project Access",
                "",
                "- Read `P2P-INTEGRATION.md` before choosing CLI or MCP.",
                *access_lines,
                "- Never access `.p2p` internals or storage/database internals directly.",
                "- Host integration files are changed only by explicit local CLI operations.",
                "",
                end,
                "",
            ]
        )
        return text.encode("utf-8")

    def _parse_section(self, content: bytes) -> "_ManagedSection | None":
        start_prefix = b"<!-- P2P:BEGIN managed-section id=" + PROJECT_INTEGRATION_SECTION_ID.encode()
        end_marker = (
            b"<!-- P2P:END managed-section id="
            + PROJECT_INTEGRATION_SECTION_ID.encode()
            + b" -->"
        )
        starts = [match.start() for match in re.finditer(re.escape(start_prefix), content)]
        ends = [match.end() for match in re.finditer(re.escape(end_marker), content)]
        if not starts and not ends:
            return None
        if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
            raise ValueError(
                "P2P_INTEGRATION_MARKER_CONFLICT: duplicate, nested, malformed, or unmatched markers"
            )
        end = ends[0]
        if content[end : end + 2] == b"\r\n":
            end += 2
        elif content[end : end + 1] in {b"\n", b"\r"}:
            end += 1
        return _ManagedSection(
            before=content[: starts[0]],
            section=content[starts[0] : end],
            after=content[end:],
        )

    def _validate_candidates(self, candidates: dict[str, bytes | None]) -> None:
        for path, content in candidates.items():
            self._safe_relative(path)
            if content is None:
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"P2P_INTEGRATION_ARTIFACT_INVALID: {path} is not UTF-8"
                ) from exc
            if _SECRET_ASSIGNMENT.search(text):
                raise ValueError(
                    f"P2P_INTEGRATION_SECRET_REJECTED: secret-shaped content in {path}"
                )

    def _safe_relative(self, value: str) -> Path:
        normalized = str(value or "").replace("\\", "/")
        relative = Path(normalized)
        if not normalized or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"P2P_INTEGRATION_PATH_UNSAFE: {value}")
        resolved = (self.root / relative).resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"P2P_INTEGRATION_PATH_UNSAFE: {value}")
        return relative

    def _current_bytes(self, relative: str) -> bytes | None:
        path = self.root / self._safe_relative(relative)
        return path.read_bytes() if path.exists() else None


@dataclass(frozen=True)
class _ManagedSection:
    before: bytes
    section: bytes
    after: bytes
