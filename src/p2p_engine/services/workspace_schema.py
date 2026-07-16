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
    ALIGNMENT_OWNER_INPUT_REQUIRED,
    ALIGNMENT_RECOVERY_REQUIRED,
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    LAYOUT_AHEAD,
    LAYOUT_CURRENT,
    LAYOUT_INCOMPLETE,
    LAYOUT_INVALID,
    LAYOUT_LEGACY,
    LAYOUT_UNSUPPORTED,
    LAYOUT_UPGRADEABLE,
    WORKSPACE_SCHEMA_CONTRACT_VERSION,
    AppliedWorkspaceMigration,
    WorkspaceDiagnostic,
    WorkspaceSchemaState,
    WorkspaceSchemaStatus,
)
from p2p_engine.foundation.files import read_yaml_mapping, write_yaml_atomic
from p2p_engine.services.workspace_migration_registry import WorkspaceMigrationRegistry
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
        "applied_migrations",
    }
)
_MIGRATION_KEYS = frozenset({"id", "from", "to", "applied_at", "actor", "plan_fingerprint_sha256"})


class WorkspaceSchemaService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        registry: WorkspaceMigrationRegistry | None = None,
        engine_version: str = __version__,
        recovery_status: Callable[[], Any] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir
        self.path = self.root / WORKSPACE_SCHEMA_PATH
        self.registry = registry or WorkspaceMigrationRegistry()
        self.engine_version = engine_version
        self.recovery_status = recovery_status

    def status(self) -> WorkspaceSchemaStatus:
        recovery = self._recovery_summary()
        if not self.path.exists():
            support = self.registry.resolve_path(0, 1)[0].runtime_support(self.engine_version)
            alignment = ALIGNMENT_RECOVERY_REQUIRED if recovery.get("required") else self._legacy_alignment()
            findings = [
                WorkspaceDiagnostic(
                    code="P2P300_WORKSPACE_SCHEMA_LEGACY_UNDECLARED",
                    severity="info",
                    path=str(WORKSPACE_SCHEMA_PATH),
                    message="Workspace schema is undeclared and remains available for read-only inspection and planning.",
                    suggested_command="p2p workspace migrate plan --to 1",
                )
            ]
            if not support.plan:
                findings.append(
                    WorkspaceDiagnostic(
                        code="P2P301_WORKSPACE_SCHEMA_RUNTIME_PREREQUISITE",
                        severity="warning",
                        path=str(WORKSPACE_SCHEMA_PATH),
                        message=(
                            "The active P2P Engine runtime can inspect this workspace but does not satisfy "
                            f"the migration planner requirement {support.plan_requires}."
                        ),
                    )
                )
            return WorkspaceSchemaStatus(
                schema_path=str(WORKSPACE_SCHEMA_PATH),
                state="legacy_undeclared",
                layout_status=LAYOUT_LEGACY,
                alignment_status=alignment,
                current_version=0,
                target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
                findings=tuple(findings),
                transition_support=support,
                recovery=recovery,
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

        if state.contract_version > WORKSPACE_SCHEMA_CONTRACT_VERSION:
            return self._unsupported(state, recovery)
        if state.current_version > CURRENT_WORKSPACE_SCHEMA_VERSION:
            return WorkspaceSchemaStatus(
                schema_path=str(WORKSPACE_SCHEMA_PATH),
                state="ahead_of_runtime",
                layout_status=LAYOUT_AHEAD,
                alignment_status=ALIGNMENT_DEGRADED,
                current_version=state.current_version,
                target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
                contract_version=state.contract_version,
                schema=state,
                findings=(
                    WorkspaceDiagnostic(
                        code="P2P304_WORKSPACE_SCHEMA_AHEAD",
                        severity="error",
                        path=str(WORKSPACE_SCHEMA_PATH),
                        message=(
                            f"Workspace schema {state.current_version} is ahead of runtime support "
                            f"{CURRENT_WORKSPACE_SCHEMA_VERSION}."
                        ),
                    ),
                ),
                recovery=recovery,
            )

        layout_findings = self.layout_findings(state.current_version)
        layout_status = (
            LAYOUT_CURRENT
            if state.current_version == CURRENT_WORKSPACE_SCHEMA_VERSION
            else LAYOUT_UPGRADEABLE
        )
        alignment = ALIGNMENT_ALIGNED
        if recovery.get("required"):
            alignment = ALIGNMENT_RECOVERY_REQUIRED
        elif layout_findings or self._alignment_advisories():
            alignment = ALIGNMENT_DEGRADED
        findings = list(layout_findings)
        findings.extend(self._alignment_advisories())
        transition_support = None
        if layout_status == LAYOUT_UPGRADEABLE:
            path = self.registry.resolve_path(state.current_version, CURRENT_WORKSPACE_SCHEMA_VERSION)
            if path:
                transition_support = path[0].runtime_support(self.engine_version)
            findings.append(
                WorkspaceDiagnostic(
                    code="P2P308_WORKSPACE_SCHEMA_UPGRADE_AVAILABLE",
                    severity="info",
                    path=str(WORKSPACE_SCHEMA_PATH),
                    message=(
                        f"Workspace schema {state.current_version} remains operable and can be upgraded "
                        f"to {CURRENT_WORKSPACE_SCHEMA_VERSION}."
                    ),
                    suggested_command=(
                        f"p2p workspace migrate plan --to {CURRENT_WORKSPACE_SCHEMA_VERSION} --format json"
                    ),
                )
            )
        return WorkspaceSchemaStatus(
            schema_path=str(WORKSPACE_SCHEMA_PATH),
            state="current" if layout_status == LAYOUT_CURRENT else "upgrade_available",
            layout_status=layout_status,
            alignment_status=alignment,
            current_version=state.current_version,
            target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            contract_version=state.contract_version,
            schema=state,
            findings=tuple(findings),
            transition_support=transition_support,
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
        raw_history = raw.get("applied_migrations", [])
        if not isinstance(raw_history, list):
            raise ValueError("workspace_schema.applied_migrations must be a sequence")
        history: list[AppliedWorkspaceMigration] = []
        for index, item in enumerate(raw_history):
            history.append(self._parse_history_item(item, index))
        state = WorkspaceSchemaState(
            contract_version=contract_version,
            current_version=current_version,
            baseline=baseline,
            initialized_at=initialized_at,
            initialized_by=initialized_by,
            applied_migrations=tuple(history),
        )
        self._validate_history(state)
        return state

    def write_state(self, state: WorkspaceSchemaState) -> None:
        self._validate_history(state)
        write_yaml_atomic(self.path, state.to_payload())

    def initialized_current_payload(self, *, initialized_at: str, actor: str) -> dict[str, object]:
        return WorkspaceSchemaState(
            contract_version=WORKSPACE_SCHEMA_CONTRACT_VERSION,
            current_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            baseline="initialized_current",
            initialized_at=initialized_at,
            initialized_by=actor,
            applied_migrations=(),
        ).to_payload()

    def layout_requirements(self, version: int) -> dict[str, tuple[str, ...]]:
        if version not in {1, 2}:
            return {"canonical": (), "optional": (), "compatibility": (), "derived": (), "transient": ()}
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
        if version >= 2:
            canonical.append(".p2p/project/questions.yml")
        return {
            "canonical": tuple(canonical),
            "optional": (
                ".p2p/project/interaction-style.yml",
                ".p2p/project/rubrics.yml",
                ".p2p/agent-integrations.yml",
            ),
            "compatibility": (".p2p/domain/",),
            "derived": (".p2p/registries/", ".p2p/project/features/", "outputs/"),
            "transient": (".p2p/.internal/workspace-migrations/",),
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
                        suggested_command="p2p workspace migrate recovery status",
                    )
                )
        if version >= 2:
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
                    legacy_sections = [
                        str(item.get("id") or "")
                        for item in sections
                        if isinstance(item, dict) and item.get("open_questions")
                    ]
                    if legacy_sections:
                        findings.append(
                            WorkspaceDiagnostic(
                                code="P2P354_LEGACY_PROJECT_QUESTIONS_PRESENT",
                                severity="error",
                                path=".p2p/project/definition.yml",
                                message=(
                                    "Workspace schema v2 requires definition open_questions to be empty: "
                                    + ", ".join(sorted(legacy_sections))
                                ),
                                suggested_command="p2p workspace migrate plan --to 2 --format json",
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
        return findings

    def validation_findings(self) -> list[WorkspaceDiagnostic]:
        status = self.status()
        findings = list(status.findings)
        if bool(status.recovery.get("required", False)):
            findings.append(
                WorkspaceDiagnostic(
                    code="P2P307_WORKSPACE_MIGRATION_RECOVERY_REQUIRED",
                    severity="error",
                    path=str(status.recovery.get("journal_path") or status.schema_path),
                    message="An interrupted workspace migration must be recovered before governed writes.",
                    suggested_command="p2p workspace migrate recovery status",
                )
            )
        return findings

    def _parse_history_item(self, item: object, index: int) -> AppliedWorkspaceMigration:
        if not isinstance(item, dict):
            raise ValueError(f"applied_migrations[{index}] must be a mapping")
        unknown = set(item) - _MIGRATION_KEYS
        if unknown:
            raise ValueError(
                f"Unknown fields in applied_migrations[{index}]: {', '.join(sorted(unknown))}"
            )
        source_raw = item.get("from")
        source = 0 if source_raw == "legacy_undeclared" else _coerce_int(source_raw, f"applied_migrations[{index}].from")
        return AppliedWorkspaceMigration(
            migration_id=_required_text(item, "id"),
            source_version=source,
            target_version=_coerce_int(item.get("to"), f"applied_migrations[{index}].to"),
            applied_at=_required_text(item, "applied_at"),
            actor=_required_text(item, "actor"),
            plan_fingerprint_sha256=_required_text(item, "plan_fingerprint_sha256"),
        )

    def _validate_history(self, state: WorkspaceSchemaState) -> None:
        if state.contract_version < 1 or state.current_version < 1:
            raise ValueError("Workspace schema contract and current versions must be positive integers")
        seen: set[str] = set()
        expected_source = (
            0
            if state.baseline == "migrated_legacy"
            else (state.applied_migrations[0].source_version if state.applied_migrations else state.current_version)
        )
        for item in state.applied_migrations:
            if item.migration_id in seen:
                raise ValueError(f"Duplicate applied workspace migration id: {item.migration_id}")
            seen.add(item.migration_id)
            transition = self.registry.transition_by_id(item.migration_id)
            if item.source_version != expected_source:
                raise ValueError("Applied workspace migration history is not contiguous")
            if (item.source_version, item.target_version) != (
                transition.source_version,
                transition.target_version,
            ):
                raise ValueError(f"Applied migration versions do not match registry: {item.migration_id}")
            expected_source = item.target_version
        if state.applied_migrations and expected_source != state.current_version:
            raise ValueError("Applied migration history does not end at current_version")
        if state.baseline == "migrated_legacy" and not state.applied_migrations:
            raise ValueError("migrated_legacy baseline requires applied migration history")
        if state.baseline == "initialized_current" and state.applied_migrations:
            raise ValueError("initialized_current baseline cannot contain applied migration history")
        if state.baseline == "migrated_declared" and not state.applied_migrations:
            raise ValueError("migrated_declared baseline requires applied migration history")

    def _unsupported(self, state: WorkspaceSchemaState, recovery: dict[str, object]) -> WorkspaceSchemaStatus:
        return WorkspaceSchemaStatus(
            schema_path=str(WORKSPACE_SCHEMA_PATH),
            state="unsupported_contract",
            layout_status=LAYOUT_UNSUPPORTED,
            alignment_status=ALIGNMENT_DEGRADED,
            current_version=state.current_version,
            target_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            contract_version=state.contract_version,
            schema=state,
            findings=(
                WorkspaceDiagnostic(
                    code="P2P303_WORKSPACE_SCHEMA_UNSUPPORTED_CONTRACT",
                    severity="error",
                    path=str(WORKSPACE_SCHEMA_PATH),
                    message=(
                        f"Workspace schema contract {state.contract_version} is newer than supported "
                        f"contract {WORKSPACE_SCHEMA_CONTRACT_VERSION}."
                    ),
                ),
            ),
            recovery=recovery,
        )

    def _legacy_alignment(self) -> str:
        project = self._project_payload()
        project_data = project.get("project") if isinstance(project, dict) else None
        domain = str(project_data.get("domain") or "") if isinstance(project_data, dict) else ""
        if domain == "software" and not (self.p2p_dir / "project" / "vertical.yml").exists():
            return ALIGNMENT_OWNER_INPUT_REQUIRED
        return ALIGNMENT_DEGRADED

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
