from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from p2p_engine.core.authority import AuthorityContext, ProjectAuthorityDescriptor
from p2p_engine.core.mutation_preview import semantic_sha256, source_precondition
from p2p_engine.core.project_domain import ProjectDomainRef, StructureSource
from p2p_engine.core.project_structure import ProjectStructure
from p2p_engine.core.project_verticals import VerticalPack
from p2p_engine.core.runtime_contract import RUNTIME_SETUP_GUIDE_MARKER
from p2p_engine.core.workspace_schema import (
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    WORKSPACE_SCHEMA_CONTRACT_VERSION,
    WorkspaceSchemaState,
)
from p2p_engine.services.agent_instructions import AgentInstructionsResult
from p2p_engine.services.agent_selection import AgentProfileSelection, select_agent_profile
from p2p_engine.services.mcp_hints import McpHint, build_mcp_hint
from p2p_engine.services.project_domain import (
    initial_project_domain_state,
    project_domain_state_bytes,
    structure_source_bytes,
)
from p2p_engine.services.project_maturity import rubrics_payload
from p2p_engine.services.project_structure import (
    initial_project_structure_event,
    project_structure_bytes,
    project_structure_events_bytes,
    project_structure_from_vertical_pack,
)
from p2p_engine.services.readiness import DEFAULT_READINESS_PROFILE_ID
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.authority import ProjectAuthorityService
from p2p_engine.services.runtime_contract import RuntimeContractService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter

def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def _yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def _domain_descriptor(
    key: str | None,
    *,
    name: str,
    source: str,
    external_ref: str | None,
) -> ProjectDomainRef | None:
    if key is None or not str(key).strip():
        if name or external_ref:
            raise ValueError(
                "P2P_PROJECT_DOMAIN_INVALID: domain name or external reference requires a domain key"
            )
        return None
    normalized_key = str(key).strip()
    display_name = name.strip() or normalized_key.replace("_", " ").replace("-", " ").title()
    return ProjectDomainRef(
        key=normalized_key,
        name=display_name,
        source=source,
        external_ref=external_ref,
    )


@dataclass(frozen=True)
class ProjectInitializationResult:
    created: list[Path]
    agent_selection: AgentProfileSelection
    agent_instructions: AgentInstructionsResult
    mcp_hint: McpHint
    warnings: list[str]
    domain: ProjectDomainRef | None
    structure_source: StructureSource
    structure_origin: dict[str, object]
    structure_revision: int
    structure_checksum: str


class ProjectInitializationService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        readiness_default_profile_payload: Callable[[], dict[str, object]],
        permissions_default_policy_payload: Callable[..., dict[str, object]],
        refresh_agent_instructions: Callable[..., AgentInstructionsResult],
        select_agent_profile_fn: Callable[[str | None], AgentProfileSelection] = select_agent_profile,
        build_mcp_hint_fn: Callable[..., McpHint] = build_mcp_hint,
        resolve_structure_pack: Callable[[StructureSource], VerticalPack | None] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.readiness_default_profile_payload = readiness_default_profile_payload
        self.permissions_default_policy_payload = permissions_default_policy_payload
        self.refresh_agent_instructions = refresh_agent_instructions
        self.select_agent_profile = select_agent_profile_fn
        self.build_mcp_hint = build_mcp_hint_fn
        self.resolve_structure_pack = resolve_structure_pack

    def init_project(
        self,
        name: str,
        agent_profile: str | None = None,
        project_domain: str | None = None,
        project_domain_name: str = "",
        project_domain_source: str = "local",
        project_domain_external_ref: str | None = None,
        structure_source: StructureSource | None = None,
        structure_origin: dict[str, object] | None = None,
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
        authority_context: AuthorityContext | None = None,
        structure_pack: VerticalPack | None = None,
    ) -> list[Path]:
        return self.init_project_with_summary(
            name=name,
            agent_profile=agent_profile,
            project_domain=project_domain,
            project_domain_name=project_domain_name,
            project_domain_source=project_domain_source,
            project_domain_external_ref=project_domain_external_ref,
            structure_source=structure_source,
            structure_origin=structure_origin,
            rubric_enabled=rubric_enabled,
            owner=owner,
            authority_context=authority_context,
            structure_pack=structure_pack,
        ).created

    def init_project_with_summary(
        self,
        name: str,
        agent_profile: str | None = None,
        project_domain: str | None = None,
        project_domain_name: str = "",
        project_domain_source: str = "local",
        project_domain_external_ref: str | None = None,
        structure_source: StructureSource | None = None,
        structure_origin: dict[str, object] | None = None,
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
        authority_context: AuthorityContext | None = None,
        structure_pack: VerticalPack | None = None,
    ) -> ProjectInitializationResult:
        is_new_project = not (self.p2p_dir / "project.yml").exists()
        agent_selection = self.select_agent_profile(agent_profile)
        domain_descriptor = _domain_descriptor(
            project_domain,
            name=project_domain_name,
            source=project_domain_source,
            external_ref=project_domain_external_ref,
        )
        selected_structure_source = structure_source or StructureSource.starter("generic")
        selected_structure_origin = dict(
            structure_origin
            or {
                "kind": "starter",
                "identity": selected_structure_source.starter_id,
                "checksum": None,
            }
        )
        resolved_structure_pack = structure_pack
        if resolved_structure_pack is None and self.resolve_structure_pack is not None:
            resolved_structure_pack = self.resolve_structure_pack(selected_structure_source)
        initialized_at = date.today().isoformat()
        initial_structure = project_structure_from_vertical_pack(
            project_id=_slugify(name),
            pack=resolved_structure_pack,
            source=selected_structure_source,
            origin=selected_structure_origin,
            actor=owner or "owner",
            applied_at=initialized_at,
            rubric_enabled=rubric_enabled,
        )
        permissions_payload = self.permissions_default_policy_payload(owner_name=owner)
        authority_descriptor = self._bootstrap_authority_descriptor(
            is_new_project=is_new_project,
            owner=owner,
            authority_context=authority_context,
        )
        files = self._bootstrap_files(
            name=name,
            domain_descriptor=domain_descriptor,
            structure_source=selected_structure_source,
            structure_origin=selected_structure_origin,
            rubric_enabled=rubric_enabled,
            owner=owner,
            permissions_payload=permissions_payload,
            authority_descriptor=authority_descriptor,
            initial_structure=initial_structure,
        )
        created = self._write_missing_files(
            files,
            actor=(
                authority_context.executor.identity_id
                if authority_context is not None
                else owner or "owner"
            ),
        )
        warnings = self._setup_guide_warnings()
        created.extend(self._create_missing_directories())
        mcp_hint = self.build_mcp_hint(self.root, project_name=name)
        instructions = self.refresh_agent_instructions(
            profile=agent_selection.effective_profile,
        )
        for path in [*instructions.created, *instructions.updated]:
            if path not in created:
                created.append(path)
        return ProjectInitializationResult(
            created=created,
            agent_selection=agent_selection,
            agent_instructions=instructions,
            mcp_hint=mcp_hint,
            warnings=warnings,
            domain=domain_descriptor,
            structure_source=selected_structure_source,
            structure_origin=selected_structure_origin,
            structure_revision=1,
            structure_checksum=initial_structure.checksum,
        )

    def _bootstrap_files(
        self,
        *,
        name: str,
        domain_descriptor: ProjectDomainRef | None,
        structure_source: StructureSource,
        structure_origin: dict[str, object],
        rubric_enabled: dict[str, bool] | None,
        owner: str | None,
        permissions_payload: dict[str, object],
        authority_descriptor: ProjectAuthorityDescriptor | None,
        initial_structure: ProjectStructure,
    ) -> dict[Path, str]:
        runtime_service = RuntimeContractService(root=self.root, p2p_dir=self.p2p_dir)
        is_new_project = not (self.p2p_dir / "project.yml").exists()
        files: dict[Path, str] = {
            self.p2p_dir / "project.yml": _yaml_dump(
                {
                    "project": {
                        "id": _slugify(name),
                        "name": name,
                        "version": "0.1.0",
                        "status": "active",
                    },
                    "runtime_contract": {"required": True},
                    "storage": {
                        "mode": "file_based",
                        "documents_format": "markdown",
                        "structured_data_format": "yaml",
                    },
                    "workflow": {"current_phase": "cli_managed"},
                    "ai": {"mode": "prompt_only", "direct_invocation": False},
                }
            ),
            self.p2p_dir / "project" / "domain.yml": project_domain_state_bytes(
                initial_project_domain_state(
                    domain_descriptor,
                    actor=owner or "owner",
                    initialized_at=date.today().isoformat(),
                    project_memory_revision=semantic_sha256(
                        {
                            "project": _slugify(name),
                            "structure_source": structure_source.to_dict(),
                            "structure_origin": structure_origin,
                        }
                    ),
                )
            ).decode("ascii"),
            self.p2p_dir / "project" / "structure-source.yml": structure_source_bytes(
                structure_source,
                origin=structure_origin,
                initialized_at=date.today().isoformat(),
                initialized_by=owner or "owner",
            ).decode("ascii"),
            self.p2p_dir / "project" / "structure.yml": project_structure_bytes(
                initial_structure
            ).decode("ascii"),
            self.p2p_dir / "project" / "structure-events.yml": (
                project_structure_events_bytes(
                    structure_id=initial_structure.structure_id,
                    events=(
                        initial_project_structure_event(
                            initial_structure,
                            actor=owner or "owner",
                            occurred_at=date.today().isoformat(),
                        ),
                    ),
                ).decode("ascii")
            ),
            self.p2p_dir / "governance" / "constitution.md": "# Constitution\n\nPending.\n",
            self.p2p_dir / "governance" / "decision-rules.md": "# Decision Rules\n\nPending.\n",
            self.p2p_dir / "governance" / "relevance-criteria.md": "# Relevance Criteria\n\nPending.\n",
            self.p2p_dir / "templates" / "proposal-template.md": "# {{ proposal_id }} - {{ title }}\n",
            self.p2p_dir / "templates" / "decision-template.md": "# Decision - {{ proposal_id }}\n",
            self.p2p_dir / "templates" / "execution-plan-template.md": "# Execution Plan - {{ proposal_id }}\n",
            self.p2p_dir / "templates" / "tasks-template.yml": "tasks: []\n",
            self.p2p_dir
            / "config"
            / "readiness-profiles"
            / f"{DEFAULT_READINESS_PROFILE_ID}.yml": _yaml_dump(self.readiness_default_profile_payload()),
            self.p2p_dir / "project" / "rubrics.yml": _yaml_dump(
                rubrics_payload(
                    (
                        structure_source.starter_id
                        if structure_source.kind == "starter"
                        else "empty"
                    ),
                    rubric_enabled=rubric_enabled,
                )
            ),
            self.p2p_dir / "project" / "permissions.yml": _yaml_dump(
                permissions_payload
            ),
        }
        if is_new_project:
            question_service = ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir)
            empty_questions = question_service.empty_artifact(
                project_id=_slugify(name),
                vertical_id="unselected",
                vertical_version="0",
                lock_checksum="unlocked",
                actor=owner or "owner",
                audit_at=date.today().isoformat(),
            )
            files[self.p2p_dir / "project" / "questions.yml"] = _yaml_dump(
                empty_questions.to_payload()
            )
        if is_new_project:
            files[runtime_service.contract_path] = _yaml_dump(runtime_service.default_contract_payload())
            files[runtime_service.setup_guide_path] = runtime_service.render_setup_guide()
            schema = WorkspaceSchemaState(
                contract_version=WORKSPACE_SCHEMA_CONTRACT_VERSION,
                current_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
                baseline="initialized_current",
                initialized_at=date.today().isoformat(),
                initialized_by=owner or "owner",
            )
            files[self.p2p_dir / "project" / "workspace-schema.yml"] = _yaml_dump(
                schema.to_payload()
            )
            if authority_descriptor is None:
                raise ValueError(
                    "P2P_AUTHORITY_CONTEXT_INVALID: new project authority is missing"
                )
            files[self.p2p_dir / "project" / "authority.yml"] = (
                ProjectAuthorityService(
                    root=self.root,
                    p2p_dir=self.p2p_dir,
                )
                .descriptor_bytes(authority_descriptor)
                .decode("ascii")
            )
        return files

    def _write_missing_files(
        self,
        files: dict[Path, str],
        *,
        actor: str,
    ) -> list[Path]:
        created: list[Path] = []
        canonical = {
            path.relative_to(self.root).as_posix(): content.encode("utf-8")
            for path, content in files.items()
            if path.is_relative_to(self.p2p_dir) and not path.exists()
        }
        if canonical:
            preview_token = semantic_sha256(
                {
                    "operation": "project.bootstrap",
                    "candidates": {
                        path: semantic_sha256({"content": content.decode("utf-8")})
                        for path, content in sorted(canonical.items())
                    },
                }
            )
            result = AtomicMutationWriter(
                root=self.root,
                p2p_dir=self.p2p_dir,
            ).apply(
                operation_id="project-bootstrap",
                candidates=canonical,
                sources=tuple(
                    source_precondition(path, None) for path in sorted(canonical)
                ),
                preview_token=preview_token,
                actor=actor,
            )
            if result.status != "applied":
                raise ValueError(
                    "P2P_INIT_BOOTSTRAP_FAILED: " + (result.message or result.status)
                )
            created.extend(Path(path) for path in result.changed_paths)
        for path, content in files.items():
            if path.is_relative_to(self.p2p_dir):
                continue
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(path.relative_to(self.root))
        return created
    def _bootstrap_authority_descriptor(
        self,
        *,
        is_new_project: bool,
        owner: str | None,
        authority_context: AuthorityContext | None,
    ) -> ProjectAuthorityDescriptor | None:
        service = ProjectAuthorityService(root=self.root, p2p_dir=self.p2p_dir)
        if not is_new_project:
            descriptor = service.read_descriptor()
            if authority_context is not None:
                service.validate_context(
                    authority_context,
                    required_capabilities=("project.initialize",),
                    descriptor=descriptor,
                )
            return None
        if authority_context is None:
            return service.new_local_descriptor(
                display_name=(f"Local authority for {owner}" if owner else "")
            )
        return service.descriptor_from_bootstrap_context(
            authority_context,
            display_name="External project authority",
        )

    def _setup_guide_warnings(self) -> list[str]:
        setup_path = self.root / "P2P-SETUP.md"
        if not setup_path.exists():
            return []
        if RUNTIME_SETUP_GUIDE_MARKER in setup_path.read_text(encoding="utf-8"):
            return []
        return [
            "P2P-SETUP.md already exists and is not P2P-managed; it was preserved. "
            "Review it against .p2p/project/runtime.yml."
        ]

    def _create_missing_directories(self) -> list[Path]:
        created: list[Path] = []
        for directory in (self.p2p_dir / "proposals", self.p2p_dir / "prompts"):
            if not directory.exists():
                directory.mkdir(parents=True)
                created.append(directory.relative_to(self.root))
        return created
