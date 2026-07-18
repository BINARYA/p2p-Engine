from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from p2p_engine.core.proposal_decision_diagnostics import (
    proposal_decision_diagnostic,
)
from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.foundation.markdown import (
    markdown_has_section as _markdown_has_section,
    read_markdown_section as _read_markdown_section,
)
from p2p_engine.services.consent import CONSENT_OPERATIONS
from p2p_engine.services.permissions import ACTOR_KINDS, PERMISSION_ROLES
from p2p_engine.services.readiness import (
    validate_readiness_assessment_payload,
    validate_readiness_profile_payload,
)
from p2p_engine.services.proposal_questions import validate_proposal_questions_payload
from p2p_engine.services.proposal_artifact_state import validate_proposal_artifact_state_payload
from p2p_engine.services.runtime_contract import RuntimeContractService

BUILT_IN_AGENT_ADAPTERS = ("generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode")


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    severity: str
    path: Path
    message: str
    suggested_command: str = ""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: int
    warnings: int
    infos: int
    findings: list[ValidationFinding]


class ValidationService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        duplicate_proposal_ids: Callable[[], dict[str, list[Path]]],
        registry_status: Callable[[], Any],
        agent_integrations_path: Callable[[], Path],
        permissions_path: Callable[[], Path],
        vertical_validation_findings: Callable[[], list[tuple[str, str, Path, str, str]]] | None = None,
        interaction_style_validation_findings: Callable[[], list[tuple[str, str, Path, str, str]]] | None = None,
        governance_validation_findings: Callable[[], list[tuple[str, str, Path, str, str]]] | None = None,
        runtime_validation_findings: Callable[[], list[Any]] | None = None,
        workspace_schema_validation_findings: Callable[[], list[Any]] | None = None,
        proposal_lifecycle_status: (
            Callable[[str], ProposalDecisionLifecycleView] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.duplicate_proposal_ids = duplicate_proposal_ids
        self.registry_status = registry_status
        self.agent_integrations_path = agent_integrations_path
        self.permissions_path = permissions_path
        self.vertical_validation_findings = vertical_validation_findings
        self.interaction_style_validation_findings = interaction_style_validation_findings
        self.governance_validation_findings = governance_validation_findings
        self.runtime_validation_findings = runtime_validation_findings
        self.workspace_schema_validation_findings = workspace_schema_validation_findings
        self.proposal_lifecycle_status = proposal_lifecycle_status

    def validate(self, *, registry_status_snapshot: Any | None = None) -> ValidationResult:
        findings: list[ValidationFinding] = []

        def add(
            code: str,
            severity: str,
            path: Path,
            message: str,
            suggested_command: str = "",
        ) -> None:
            findings.append(
                ValidationFinding(
                    code=code,
                    severity=severity,
                    path=_relative_to_root(path, self.root),
                    message=message,
                    suggested_command=suggested_command,
                )
            )

        self._validate_required_paths(add)
        self._validate_structured_yaml(add)
        self._validate_readiness(add)
        self._validate_proposal_questions(add)
        self._validate_proposal_artifacts(add)
        self._validate_agent_integrations(add)
        self._validate_permissions(add)
        self._validate_consents(add)
        self._validate_proposals(add)
        self._validate_project_interaction_style(add)
        self._validate_governance_policy(add)
        self._validate_runtime_contract(add)
        self._validate_workspace_schema(add)
        self._validate_project_verticals(add)
        self._validate_registries(add, registry_status_snapshot)

        errors = sum(1 for finding in findings if finding.severity == "error")
        warnings = sum(1 for finding in findings if finding.severity == "warning")
        infos = sum(1 for finding in findings if finding.severity == "info")
        return ValidationResult(
            ok=errors == 0,
            errors=errors,
            warnings=warnings,
            infos=infos,
            findings=findings,
        )

    def _validate_required_paths(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        required_paths = [
            self.p2p_dir / "project.yml",
            self.p2p_dir / "governance" / "constitution.md",
            self.p2p_dir / "governance" / "decision-rules.md",
            self.p2p_dir / "governance" / "relevance-criteria.md",
            self.p2p_dir / "templates" / "proposal-template.md",
            self.p2p_dir / "templates" / "decision-template.md",
            self.p2p_dir / "templates" / "execution-plan-template.md",
            self.p2p_dir / "templates" / "tasks-template.yml",
            self.p2p_dir / "proposals",
            self.p2p_dir / "prompts",
        ]
        for path in required_paths:
            if not path.exists():
                add("P2P001_MISSING_REQUIRED_PATH", "error", path, "Required P2P path is missing.", "")

    def _validate_structured_yaml(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        structured_files = [self.p2p_dir / "project.yml", self.p2p_dir / "agent-policy.yml"]
        structured_files.extend(self.p2p_dir.glob("config/**/*.yml"))
        structured_files.extend(self.p2p_dir.glob("registries/*.yml"))
        structured_files.extend(self.p2p_dir.glob("project/*.yml"))
        structured_files.extend(self.p2p_dir.glob("proposals/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("changes/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("choices/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("work/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("consents/*/*.yml"))
        for path in sorted(set(structured_files)):
            if path.exists() and path.is_file():
                try:
                    yaml.safe_load(path.read_text(encoding="utf-8"))
                except yaml.YAMLError as exc:
                    add("P2P010_INVALID_YAML", "error", path, f"Invalid YAML: {exc}", "")

    def _validate_readiness(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        for profile_path in sorted(self.p2p_dir.glob("config/readiness-profiles/*.yml")):
            try:
                validate_readiness_profile_payload(_read_yaml_mapping(profile_path, default={}))
            except ValueError as exc:
                add("P2P230_INVALID_READINESS_PROFILE", "error", profile_path, str(exc), "")

        for readiness_path in sorted(self.p2p_dir.glob("proposals/*/readiness.yml")):
            try:
                validate_readiness_assessment_payload(_read_yaml_mapping(readiness_path, default={}))
            except ValueError as exc:
                add("P2P231_INVALID_READINESS_ASSESSMENT", "error", readiness_path, str(exc), "")

    def _validate_proposal_questions(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        for questions_path in sorted(self.p2p_dir.glob("proposals/*/questions.yml")):
            try:
                validate_proposal_questions_payload(_read_yaml_mapping(questions_path, default={}))
            except ValueError as exc:
                add("P2P232_INVALID_PROPOSAL_QUESTIONS", "error", questions_path, str(exc), "")

    def _validate_proposal_artifacts(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        for artifact_path in sorted(self.p2p_dir.glob("proposals/*/artifact-state.yml")):
            try:
                validate_proposal_artifact_state_payload(_read_yaml_mapping(artifact_path, default={}))
            except ValueError as exc:
                add(
                    "P2P233_INVALID_PROPOSAL_ARTIFACT_STATE",
                    "error",
                    artifact_path,
                    str(exc),
                    "p2p proposal artifact init PROP-XXX",
                )

    def _validate_agent_integrations(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        path = self.agent_integrations_path()
        if not path.exists():
            return
        try:
            _validate_agent_integrations_payload(_read_yaml_mapping(path, default={}), root=self.root)
        except ValueError as exc:
            add("P2P240_INVALID_AGENT_INTEGRATIONS", "error", path, str(exc), "")

    def _validate_permissions(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        path = self.permissions_path()
        if not path.exists():
            return
        try:
            permissions = _read_yaml_mapping(path, default={})
        except ValueError as exc:
            add("P2P210_INVALID_PERMISSIONS", "error", path, str(exc), "")
            permissions = {}
        identities = permissions.get("identities", {})
        if not isinstance(identities, dict) or not identities:
            add("P2P211_INVALID_PERMISSIONS_IDENTITIES", "error", path, "permissions.yml must define identities.", "")
            return

        has_owner = False
        for actor_id, actor in identities.items():
            if not isinstance(actor, dict):
                add("P2P212_INVALID_PERMISSION_ACTOR", "error", path, f"Actor must be a mapping: {actor_id}", "")
                continue
            role = str(actor.get("role") or "")
            kind = str(actor.get("kind") or "")
            if role not in PERMISSION_ROLES:
                add("P2P213_INVALID_PERMISSION_ROLE", "error", path, f"Invalid role for {actor_id}: {role}", "")
            if kind not in ACTOR_KINDS:
                add("P2P214_INVALID_ACTOR_KIND", "error", path, f"Invalid actor kind for {actor_id}: {kind}", "")
            has_owner = has_owner or role == "owner"
        if not has_owner:
            add("P2P215_MISSING_OWNER_IDENTITY", "error", path, "permissions.yml must define at least one owner identity.", "")

    def _validate_consents(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        for consent_path in sorted(self.p2p_dir.glob("consents/CONSENT-*/consent.yml")):
            consent_dir_id = consent_path.parent.name
            try:
                consent = _read_yaml_mapping(consent_path, default={})
            except ValueError as exc:
                add("P2P220_INVALID_CONSENT", "error", consent_path, str(exc), "")
                continue
            consent_id = str(consent.get("consent_id") or "")
            if consent_id != consent_dir_id:
                add(
                    "P2P221_CONSENT_ID_MISMATCH",
                    "error",
                    consent_path,
                    f"Consent ID {consent_id} does not match directory {consent_dir_id}.",
                    "",
                )
            operation = str(consent.get("operation") or "")
            if operation not in CONSENT_OPERATIONS:
                add("P2P222_INVALID_CONSENT_OPERATION", "error", consent_path, f"Invalid consent operation: {operation}", "")
            status = str(consent.get("status") or "")
            if status not in {"requested", "granted", "consumed", "revoked", "expired", "used_with_error"}:
                add("P2P223_INVALID_CONSENT_STATUS", "error", consent_path, f"Invalid consent status: {status}", "")
            required_fields = ["target", "actor_id", "created_at"]
            if status != "requested":
                required_fields.append("approved_by")
            for required in required_fields:
                if not str(consent.get(required) or "").strip():
                    add("P2P224_MISSING_CONSENT_FIELD", "error", consent_path, f"Consent receipt missing required field: {required}", "")

    def _validate_proposals(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        proposals_dir = self.p2p_dir / "proposals"
        if not proposals_dir.exists():
            return

        duplicate_ids = self.duplicate_proposal_ids()
        for proposal_id, paths in duplicate_ids.items():
            relative_paths = ", ".join(str(_relative_to_root(path, self.root)) for path in paths)
            add(
                "P2P104_DUPLICATE_PROPOSAL_ID",
                "error",
                proposals_dir,
                f"Duplicate proposal ID {proposal_id} found in: {relative_paths}.",
                "rename or retire duplicate proposal directories, then run p2p registry refresh",
            )

        for proposal_dir in sorted(path for path in proposals_dir.iterdir() if path.is_dir()):
            match = re.match(r"^(PROP-\d{3})-[a-z0-9][a-z0-9-]*$", proposal_dir.name)
            if not match:
                add(
                    "P2P100_INVALID_PROPOSAL_DIRECTORY",
                    "error",
                    proposal_dir,
                    "Proposal directory must be named PROP-XXX-slug.",
                    "",
                )
                proposal_id = proposal_dir.name.split("-", 2)[0]
            else:
                proposal_id = match.group(1)
            proposal_path = proposal_dir / "proposal.md"
            decision_path = proposal_dir / "decision.md"
            if not proposal_path.exists():
                add("P2P101_MISSING_PROPOSAL_FILE", "error", proposal_path, "proposal.md is missing.", "")
                continue
            proposal_text = proposal_path.read_text(encoding="utf-8")
            for section in ("Status", "Problem", "Proposal", "Decision"):
                if not _markdown_has_section(proposal_text, section):
                    add(
                        "P2P102_MISSING_PROPOSAL_SECTION",
                        "error",
                        proposal_path,
                        f"proposal.md is missing required section: {section}.",
                        "",
                    )
            proposal_status = _read_proposal_status(proposal_path)
            if proposal_status == "unknown":
                add(
                    "P2P103_MISSING_PROPOSAL_STATUS",
                    "error",
                    proposal_path,
                    "proposal.md is missing a machine-readable status.",
                    "",
                )
            lifecycle = (
                self.proposal_lifecycle_status(proposal_id)
                if (
                    self.proposal_lifecycle_status is not None
                    and proposal_id not in duplicate_ids
                )
                else None
            )
            if lifecycle is not None:
                for diagnostic in lifecycle.diagnostics:
                    if diagnostic.startswith(
                        "P2P362_DECISION_PROJECTION_DIVERGENCE"
                    ):
                        target = (
                            proposal_path
                            if diagnostic.endswith("proposal.md")
                            else decision_path
                        )
                        add(
                            "P2P362_DECISION_PROJECTION_DIVERGENCE",
                            "warning",
                            target,
                            diagnostic,
                            (
                                f"p2p decision projection-repair preview "
                                f"{proposal_id}"
                            ),
                        )
                    elif diagnostic.startswith(
                        "P2P377_DECISION_PROPOSAL_BINDING_DIVERGED"
                    ):
                        add(
                            "P2P377_DECISION_PROPOSAL_BINDING_DIVERGED",
                            "error",
                            proposal_path,
                            diagnostic,
                            f"p2p decision status {proposal_id}",
                        )
                    elif diagnostic.startswith(
                        "P2P307_WORKSPACE_MIGRATION_RECOVERY_REQUIRED"
                    ):
                        # Workspace-schema validation owns this diagnostic.
                        continue
                    else:
                        definition = proposal_decision_diagnostic(diagnostic)
                        code = (
                            definition.code
                            if definition is not None
                            else "P2P361_DECISION_LEDGER_INVALID"
                        )
                        severity = (
                            definition.severity
                            if definition is not None
                            else "error"
                        )
                        target = proposal_dir / "decision-events.yml"
                        suggested_command = f"p2p decision status {proposal_id}"
                        if code == "P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED":
                            if lifecycle.source_model == "legacy_projection_v2":
                                target = decision_path
                                suggested_command = (
                                    "p2p workspace migrate plan --to 3 "
                                    "--format json"
                                )
                        elif code == (
                            "P2P378_DECISION_RECONSIDERATION_REQUIRES_NEW_PROPOSAL"
                        ):
                            target = proposal_path
                            suggested_command = (
                                lifecycle.suggested_next_command
                                or f"p2p decision status {proposal_id}"
                            )
                        add(
                            code,
                            severity,
                            target,
                            diagnostic,
                            suggested_command,
                        )

            if not decision_path.exists():
                add("P2P110_MISSING_DECISION_FILE", "warning", decision_path, "decision.md is missing.", "")
            else:
                decision_text = decision_path.read_text(encoding="utf-8")
                if not _markdown_has_section(decision_text, "Status"):
                    add(
                        "P2P111_MISSING_DECISION_STATUS",
                        "warning",
                        decision_path,
                        "decision.md is missing Status section.",
                        "",
                    )
                decision_status = (_read_markdown_section(decision_text, "Status") or "").strip("`")
                if (
                    lifecycle is None
                    and
                    proposal_status in {"accepted", "rejected", "deferred"}
                    and decision_status
                    and decision_status != proposal_status
                ):
                    add(
                        "P2P112_STATUS_MISMATCH",
                        "warning",
                        decision_path,
                        f"Proposal status is {proposal_status}, but decision status is {decision_status}.",
                        f"p2p proposal show {proposal_id}",
                    )

    def _validate_registries(
        self,
        add: Callable[[str, str, Path, str, str], None],
        registry_status_snapshot: Any | None = None,
    ) -> None:
        try:
            registry_status = registry_status_snapshot or self.registry_status()
        except ValueError as exc:
            add(
                "P2P200_REGISTRY_STATUS_ERROR",
                "warning",
                self.p2p_dir / "registries",
                f"Could not inspect registries: {exc}",
                "p2p registry refresh",
            )
        else:
            if registry_status.stale:
                add(
                    "P2P201_STALE_REGISTRY",
                    "warning",
                    registry_status.registries_dir,
                    "Generated registries are missing or stale.",
                    "p2p registry refresh",
                )

    def _validate_project_verticals(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        if self.vertical_validation_findings is None:
            return
        for code, severity, path, message, suggested_command in self.vertical_validation_findings():
            add(code, severity, path, message, suggested_command)

    def _validate_project_interaction_style(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        if self.interaction_style_validation_findings is None:
            return
        for code, severity, path, message, suggested_command in self.interaction_style_validation_findings():
            add(code, severity, path, message, suggested_command)

    def _validate_governance_policy(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        if self.governance_validation_findings is None:
            return
        for code, severity, path, message, suggested_command in self.governance_validation_findings():
            add(code, severity, path, message, suggested_command)

    def _validate_runtime_contract(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        runtime_findings = self.runtime_validation_findings
        if runtime_findings is None:
            runtime_findings = RuntimeContractService(root=self.root, p2p_dir=self.p2p_dir).validation_findings
        for finding in runtime_findings():
            add(finding.code, finding.severity, self.root / finding.path, finding.message, finding.suggested_command)

    def _validate_workspace_schema(self, add: Callable[[str, str, Path, str, str], None]) -> None:
        if self.workspace_schema_validation_findings is None:
            return
        for finding in self.workspace_schema_validation_findings():
            add(
                finding.code,
                finding.severity,
                self.root / finding.path,
                finding.message,
                finding.suggested_command,
            )


def _relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _read_yaml_mapping(path: Path, default: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return default
    if not isinstance(data, dict):
        raise ValueError(f"YAML document must be a mapping: {_relative_to_root(path, path.parent)}")
    return data


def _read_proposal_status(path: Path) -> str:
    if not path.exists():
        return "unknown"
    text = path.read_text(encoding="utf-8")
    status = _read_markdown_section(text, "Status")
    if not status:
        return "unknown"
    return status.strip().strip("`").lower()


def _validate_agent_integrations_payload(data: dict[str, object], *, root: Path | None = None) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("Agent integrations registry must use schema_version: 1.")
    if data.get("baseline_profile") != "generic":
        raise ValueError("Agent integrations registry baseline_profile must be generic.")
    forbidden = {
        "active",
        "active_agent",
        "active_adapter",
        "current",
        "current_agent",
        "current_adapter",
        "default",
        "default_agent",
        "default_adapter",
        "preferred",
        "preferred_agent",
        "preferred_adapter",
        "use",
        "switch",
    }
    for key in forbidden:
        if key in data:
            raise ValueError(f"Agent integrations registry must not define {key}.")
    adapters = data.get("adapters")
    if not isinstance(adapters, dict):
        raise ValueError("Agent integrations registry must define adapters mapping.")
    if "generic" not in adapters:
        raise ValueError("Agent integrations registry must include generic adapter.")
    file_records_by_path: dict[str, dict[str, object]] = {}
    for adapter_id, adapter in adapters.items():
        if adapter_id not in BUILT_IN_AGENT_ADAPTERS:
            raise ValueError(f"Unknown agent adapter: {adapter_id}")
        if not isinstance(adapter, dict):
            raise ValueError(f"Agent adapter record must be a mapping: {adapter_id}")
        for required in ("status", "maturity", "template_version", "capabilities", "files"):
            if required not in adapter:
                raise ValueError(f"Agent adapter record missing {required}: {adapter_id}")
        if adapter.get("status") != "installed":
            raise ValueError(f"Agent adapter status must be installed: {adapter_id}")
        if not str(adapter.get("maturity") or "").strip():
            raise ValueError(f"Agent adapter maturity is required: {adapter_id}")
        if not str(adapter.get("template_version") or "").strip():
            raise ValueError(f"Agent adapter template_version is required: {adapter_id}")
        if not isinstance(adapter.get("capabilities"), dict):
            raise ValueError(f"Agent adapter capabilities must be a mapping: {adapter_id}")
        files = adapter.get("files")
        if not isinstance(files, list):
            raise ValueError(f"Agent adapter files must be a list: {adapter_id}")
        for record in files:
            if not isinstance(record, dict):
                raise ValueError(f"Agent adapter file record must be a mapping: {adapter_id}")
            for required in ("path", "shared", "owner", "managed", "template_id", "sha256", "drift"):
                if required not in record:
                    raise ValueError(f"Agent adapter file record missing {required}: {adapter_id}")
            relative_path = _validate_agent_file_path(record.get("path"), root=root)
            if not isinstance(record.get("shared"), bool):
                raise ValueError(f"Agent adapter file shared must be boolean: {relative_path}")
            if not isinstance(record.get("managed"), bool):
                raise ValueError(f"Agent adapter file managed must be boolean: {relative_path}")
            if record["owner"] not in BUILT_IN_AGENT_ADAPTERS:
                raise ValueError(f"Invalid agent adapter file owner: {record['owner']}")
            if not str(record.get("template_id") or "").strip():
                raise ValueError(f"Agent adapter file template_id is required: {relative_path}")
            sha256 = str(record.get("sha256") or "")
            if sha256 and not re.fullmatch(r"[0-9a-f]{64}", sha256):
                raise ValueError(f"Invalid SHA-256 for agent adapter file: {record.get('path')}")
            drift = record.get("drift")
            if drift not in {"clean", "missing", "drifted", "modified", "unmanaged", "conflicted", "stale_template"}:
                raise ValueError(f"Invalid drift state for agent adapter file: {record.get('path')}")
            if record.get("managed") is True and not sha256:
                raise ValueError(f"Managed agent file must record SHA-256: {relative_path}")
            if record.get("managed") is False and drift == "clean":
                raise ValueError(f"Unmanaged agent file must not have clean drift state: {relative_path}")
            previous = file_records_by_path.get(str(relative_path))
            if previous is not None and not _compatible_agent_file_records(previous, record):
                raise ValueError(f"Duplicate agent file path has incompatible ownership: {relative_path}")
            file_records_by_path.setdefault(str(relative_path), record)
            if root is not None and record.get("managed") is True:
                actual_path = root / relative_path
                if not actual_path.exists():
                    raise ValueError(f"Managed agent file is missing: {relative_path}")
                if _sha256_file(actual_path) != sha256:
                    raise ValueError(f"Managed agent file hash mismatch: {relative_path}")


def _validate_agent_file_path(value: object, *, root: Path | None) -> Path:
    raw_path = str(value or "").strip()
    if not raw_path:
        raise ValueError("Agent adapter file path is required.")
    relative_path = Path(raw_path)
    if relative_path.is_absolute():
        raise ValueError(f"Agent adapter file path must be relative: {raw_path}")
    if ".." in relative_path.parts:
        raise ValueError(f"Agent adapter file path must not escape project root: {raw_path}")
    if root is not None:
        resolved_root = root.resolve()
        resolved_path = (resolved_root / relative_path).resolve()
        if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
            raise ValueError(f"Agent adapter file path must not escape project root: {raw_path}")
    return relative_path


def _compatible_agent_file_records(previous: dict[str, object], current: dict[str, object]) -> bool:
    return (
        previous.get("shared") is True
        and current.get("shared") is True
        and previous.get("owner") == current.get("owner")
        and previous.get("template_id") == current.get("template_id")
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
