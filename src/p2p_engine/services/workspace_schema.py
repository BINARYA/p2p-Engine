from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from p2p_engine import __version__
from p2p_engine.core.workspace_schema import (
    ALIGNMENT_ALIGNED,
    ALIGNMENT_DEGRADED,
    ALIGNMENT_RECOVERY_REQUIRED,
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    LAYOUT_CURRENT,
    LAYOUT_INVALID,
    LAYOUT_UNSUPPORTED,
    WORKSPACE_SCHEMA_CONTRACT_VERSION,
    WorkspaceDiagnostic,
    WorkspaceSchemaState,
    WorkspaceSchemaPreflight,
    WorkspaceSchemaStatus,
)
from p2p_engine.foundation.files import read_yaml_mapping, write_yaml_atomic
from p2p_engine.services.project_questions import ProjectQuestionStateService


WORKSPACE_SCHEMA_PATH = Path(".p2p/project/workspace-schema.yml")

_ROOT_KEYS = frozenset({"workspace_schema"})
_SCHEMA_KEYS = frozenset(
    {
        "contract_version",
        "current_version",
        "baseline",
        "initialized_at",
        "initialized_by",
    }
)


class WorkspaceSchemaService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        recovery_status: Callable[[], Any] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir
        self.path = self.root / WORKSPACE_SCHEMA_PATH
        self.recovery_status = recovery_status

    def preflight(self) -> WorkspaceSchemaPreflight:
        recovery = self._recovery_summary()
        if not self.path.exists():
            return WorkspaceSchemaPreflight(
                schema_path=str(WORKSPACE_SCHEMA_PATH),
                state="unsupported_missing",
                layout_status=LAYOUT_UNSUPPORTED,
                current_version=None,
                target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
                recovery=recovery,
            )
        try:
            state = self.read_state()
        except ValueError:
            return WorkspaceSchemaPreflight(
                schema_path=str(WORKSPACE_SCHEMA_PATH),
                state="invalid",
                layout_status=LAYOUT_INVALID,
                current_version=None,
                target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
                recovery=recovery,
            )
        supported = (
            state.contract_version == WORKSPACE_SCHEMA_CONTRACT_VERSION
            and state.current_version == CURRENT_WORKSPACE_SCHEMA_VERSION
        )
        return WorkspaceSchemaPreflight(
            schema_path=str(WORKSPACE_SCHEMA_PATH),
            state="current" if supported else "unsupported_schema",
            layout_status=LAYOUT_CURRENT if supported else LAYOUT_UNSUPPORTED,
            current_version=state.current_version,
            target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            contract_version=state.contract_version,
            recovery=recovery,
        )

    def status(self) -> WorkspaceSchemaStatus:
        recovery = self._recovery_summary()
        if not self.path.exists():
            return self._unsupported(
                state=None,
                recovery=recovery,
                state_name="unsupported_missing",
                message="Workspace schema declaration is missing.",
            )

        try:
            state = self.read_state()
        except ValueError as exc:
            return WorkspaceSchemaStatus(
                schema_path=str(WORKSPACE_SCHEMA_PATH),
                state="invalid",
                layout_status=LAYOUT_INVALID,
                alignment_status=ALIGNMENT_RECOVERY_REQUIRED if recovery.get("required") else ALIGNMENT_DEGRADED,
                current_version=None,
                target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
                findings=(
                    WorkspaceDiagnostic(
                        code="P2P302_WORKSPACE_SCHEMA_INVALID",
                        severity="error",
                        path=str(WORKSPACE_SCHEMA_PATH),
                        message=str(exc),
                        suggested_command="p2p workspace schema status --format json",
                    ),
                ),
                recovery=recovery,
            )

        if (
            state.contract_version != WORKSPACE_SCHEMA_CONTRACT_VERSION
            or state.current_version != CURRENT_WORKSPACE_SCHEMA_VERSION
        ):
            return self._unsupported(
                state=state,
                recovery=recovery,
                state_name="unsupported_schema",
                message=(
                    f"Workspace contract {state.contract_version}, schema {state.current_version} "
                    "does not match the only supported contract "
                    f"{WORKSPACE_SCHEMA_CONTRACT_VERSION}, schema {CURRENT_WORKSPACE_SCHEMA_VERSION}."
                ),
            )

        layout_findings = self.layout_findings(state.current_version)
        alignment = ALIGNMENT_ALIGNED
        if recovery.get("required"):
            alignment = ALIGNMENT_RECOVERY_REQUIRED
        elif layout_findings or self._alignment_advisories():
            alignment = ALIGNMENT_DEGRADED
        findings = list(layout_findings)
        findings.extend(self._alignment_advisories())
        return WorkspaceSchemaStatus(
            schema_path=str(WORKSPACE_SCHEMA_PATH),
            state="current",
            layout_status=LAYOUT_CURRENT,
            alignment_status=alignment,
            current_version=state.current_version,
            target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            contract_version=state.contract_version,
            schema=state,
            findings=tuple(findings),
            recovery=recovery,
        )

    def read_state(self) -> WorkspaceSchemaState:
        try:
            payload = read_yaml_mapping(
                self.path,
                default={},
                error_message="Workspace schema must be a YAML mapping: {path}",
            )
        except (OSError, yaml.YAMLError, ValueError) as exc:
            raise ValueError(f"Cannot parse workspace schema: {exc}") from exc
        unknown_root = set(payload) - _ROOT_KEYS
        if unknown_root:
            raise ValueError(f"Unknown workspace schema root fields: {', '.join(sorted(unknown_root))}")
        raw = payload.get("workspace_schema")
        if not isinstance(raw, dict):
            raise ValueError("workspace_schema mapping is required")
        unknown = set(raw) - _SCHEMA_KEYS
        if unknown:
            raise ValueError(f"Unknown workspace schema fields: {', '.join(sorted(unknown))}")
        try:
            contract_version = _required_int(raw, "contract_version")
            current_version = _required_int(raw, "current_version")
            baseline = _required_text(raw, "baseline")
            initialized_at = _required_text(raw, "initialized_at")
            initialized_by = _required_text(raw, "initialized_by")
        except (TypeError, ValueError) as exc:
            raise ValueError(str(exc)) from exc
        state = WorkspaceSchemaState(
            contract_version=contract_version,
            current_version=current_version,
            baseline=baseline,
            initialized_at=initialized_at,
            initialized_by=initialized_by,
        )
        self._validate_state(state)
        return state

    def write_state(self, state: WorkspaceSchemaState) -> None:
        self._validate_state(state)
        write_yaml_atomic(self.path, state.to_payload())

    def initialized_current_payload(self, *, initialized_at: str, actor: str) -> dict[str, object]:
        return WorkspaceSchemaState(
            contract_version=WORKSPACE_SCHEMA_CONTRACT_VERSION,
            current_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            baseline="initialized_current",
            initialized_at=initialized_at,
            initialized_by=actor,
        ).to_payload()

    def layout_requirements(self, version: int) -> dict[str, tuple[str, ...]]:
        if version != CURRENT_WORKSPACE_SCHEMA_VERSION:
            return {"canonical": (), "optional": (), "derived": (), "transient": ()}
        canonical = [
            ".p2p/project.yml",
            ".p2p/project/runtime.yml",
            ".p2p/project/workspace-schema.yml",
            ".p2p/project/domain.yml",
            ".p2p/project/permissions.yml",
            ".p2p/governance/constitution.md",
            ".p2p/governance/decision-rules.md",
            ".p2p/governance/relevance-criteria.md",
            ".p2p/templates/proposal-template.md",
            ".p2p/templates/decision-template.md",
            ".p2p/templates/execution-plan-template.md",
            ".p2p/templates/tasks-template.yml",
            ".p2p/proposals",
            ".p2p/prompts",
        ]
        if (self.p2p_dir / "project" / "vertical.yml").exists():
            canonical.extend(
                [
                    ".p2p/project/vertical.lock.yml",
                    ".p2p/project/definition.yml",
                ]
            )
        canonical.append(".p2p/project/questions.yml")
        return {
            "canonical": tuple(canonical),
            "optional": (
                ".p2p/project/interaction-style.yml",
                ".p2p/project/rubrics.yml",
                ".p2p/agent-integrations.yml",
            ),
            "derived": (".p2p/registries/", ".p2p/project/features/", "outputs/"),
            "transient": (".p2p/.internal/workspace-transactions/",),
        }

    def layout_findings(self, version: int) -> list[WorkspaceDiagnostic]:
        findings: list[WorkspaceDiagnostic] = []
        for relative in self.layout_requirements(version)["canonical"]:
            if not (self.root / relative).exists():
                findings.append(
                    WorkspaceDiagnostic(
                        code="P2P305_WORKSPACE_LAYOUT_MISSING",
                        severity="error",
                        path=relative,
                        message=f"Current workspace schema requires {relative}.",
                        suggested_command="p2p workspace schema status --format json",
                    )
                )
        questions_path = self.root / ".p2p/project/questions.yml"
        if questions_path.exists():
            try:
                ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir).read()
            except ValueError as exc:
                findings.append(
                    WorkspaceDiagnostic(
                        code="P2P340_PROJECT_QUESTIONS_INVALID",
                        severity="error",
                        path=".p2p/project/questions.yml",
                        message=str(exc),
                        suggested_command="p2p project readiness questions status --format json",
                    )
                )
        definition_path = self.root / ".p2p/project/definition.yml"
        if definition_path.exists():
            try:
                definition = read_yaml_mapping(definition_path, default={})
                raw = definition.get("project_definition")
                sections = raw.get("sections") if isinstance(raw, dict) else None
                if not isinstance(sections, list):
                    raise ValueError("project_definition.sections must be a sequence")
                embedded_questions = [
                    str(item.get("id") or "")
                    for item in sections
                    if isinstance(item, dict) and "open_questions" in item
                ]
                if embedded_questions:
                    findings.append(
                        WorkspaceDiagnostic(
                            code="P2P354_EMBEDDED_PROJECT_QUESTIONS_PRESENT",
                            severity="error",
                            path=".p2p/project/definition.yml",
                            message=(
                                "Current workspace schema forbids definition open_questions: "
                                + ", ".join(sorted(embedded_questions))
                            ),
                            suggested_command="p2p project definition show --format json",
                        )
                    )
            except (OSError, ValueError, yaml.YAMLError) as exc:
                findings.append(
                    WorkspaceDiagnostic(
                        code="P2P255_PROJECT_DEFINITION_INVALID",
                        severity="error",
                        path=".p2p/project/definition.yml",
                        message=str(exc),
                        suggested_command="p2p project definition show --format json",
                    )
                )
        proposals_dir = self.p2p_dir / "proposals"
        for proposal_dir in (
            sorted(proposals_dir.iterdir(), key=lambda item: item.name)
            if proposals_dir.exists()
            else ()
        ):
            if not proposal_dir.is_dir() or not proposal_dir.name.startswith("PROP-"):
                continue
            ledger_path = proposal_dir / "decision-events.yml"
            relative = ledger_path.relative_to(self.root).as_posix()
            if not ledger_path.exists():
                findings.append(
                    WorkspaceDiagnostic(
                        code="P2P361_DECISION_LEDGER_INVALID",
                        severity="error",
                        path=relative,
                        message="Workspace schema v3 requires one decision ledger per proposal.",
                        suggested_command="p2p decision status "
                        + "-".join(proposal_dir.name.split("-", 2)[:2]),
                    )
                )
                continue
            try:
                from p2p_engine.services.proposal_decision_ledger import (
                    ProposalDecisionLedgerCodec,
                )

                ProposalDecisionLedgerCodec().loads(
                    ledger_path.read_bytes(),
                    expected_proposal_id="-".join(proposal_dir.name.split("-", 2)[:2]),
                )
            except (OSError, ValueError) as exc:
                findings.append(
                    WorkspaceDiagnostic(
                        code="P2P361_DECISION_LEDGER_INVALID",
                        severity="error",
                        path=relative,
                        message=str(exc),
                        suggested_command="p2p decision repair ledger preview "
                        + "-".join(proposal_dir.name.split("-", 2)[:2]),
                    )
                )
        return findings

    def validation_findings(self) -> list[WorkspaceDiagnostic]:
        status = self.status()
        findings = list(status.findings)
        if bool(status.recovery.get("required", False)):
            findings.append(
                WorkspaceDiagnostic(
                    code="P2P307_WORKSPACE_TRANSACTION_RECOVERY_REQUIRED",
                    severity="error",
                    path=str(status.recovery.get("journal_path") or status.schema_path),
                    message="An interrupted workspace transaction must be recovered before governed writes.",
                    suggested_command="p2p workspace schema status --format json",
                )
            )
        return findings

    def _validate_state(self, state: WorkspaceSchemaState) -> None:
        if state.contract_version < 1 or state.current_version < 1:
            raise ValueError("Workspace schema contract and current versions must be positive integers")
        if state.baseline != "initialized_current":
            raise ValueError("Workspace schema baseline must be initialized_current")

    def _unsupported(
        self,
        state: WorkspaceSchemaState | None,
        recovery: dict[str, object],
        *,
        state_name: str,
        message: str,
    ) -> WorkspaceSchemaStatus:
        return WorkspaceSchemaStatus(
            schema_path=str(WORKSPACE_SCHEMA_PATH),
            state=state_name,
            layout_status=LAYOUT_UNSUPPORTED,
            alignment_status=(
                ALIGNMENT_RECOVERY_REQUIRED
                if recovery.get("required")
                else ALIGNMENT_DEGRADED
            ),
            current_version=state.current_version if state else None,
            target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            contract_version=state.contract_version if state else None,
            schema=state,
            findings=(
                WorkspaceDiagnostic(
                    code="P2P_WORKSPACE_UNSUPPORTED_SCHEMA",
                    severity="error",
                    path=str(WORKSPACE_SCHEMA_PATH),
                    message=(
                        f"{message} P2P Engine {__version__} supports workspace schema "
                        f"{CURRENT_WORKSPACE_SCHEMA_VERSION} only and provides no in-runtime "
                        "conversion. Recreate or convert the workspace outside this runtime."
                    ),
                    suggested_command="p2p workspace schema status --format json",
                ),
            ),
            recovery=recovery,
        )

    def _alignment_advisories(self) -> list[WorkspaceDiagnostic]:
        project = self._project_payload()
        project_data = project.get("project") if isinstance(project, dict) else None
        domain = str(project_data.get("domain") or "") if isinstance(project_data, dict) else ""
        if domain == "software" and not (self.p2p_dir / "project" / "vertical.yml").exists():
            return [
                WorkspaceDiagnostic(
                    code="P2P306_SOFTWARE_VERTICAL_FALLBACK",
                    severity="warning",
                    path=".p2p/project/vertical.yml",
                    message="Software-domain workspace uses fallback vertical context.",
                    suggested_command="p2p project vertical list",
                )
            ]
        return []

    def _project_payload(self) -> dict[str, object]:
        path = self.p2p_dir / "project.yml"
        if not path.exists():
            return {}
        try:
            return read_yaml_mapping(path, default={})
        except (OSError, ValueError, yaml.YAMLError):
            return {}

    def _recovery_summary(self) -> dict[str, object]:
        if self.recovery_status is None:
            return {}
        try:
            result = self.recovery_status()
        except (OSError, ValueError):
            return {"required": True, "state": "invalid"}
        return result.to_dict() if hasattr(result, "to_dict") else dict(result or {})


def _required_text(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if isinstance(value, (date, datetime)):
        return value.isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _required_int(mapping: dict[str, object], key: str) -> int:
    return _coerce_int(mapping.get(key), key)


def _coerce_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value
