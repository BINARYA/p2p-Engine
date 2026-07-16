from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import yaml

from p2p_engine.core.workspace_schema import (
    FINDING_DEGRADED,
    FINDING_INVALID,
    FINDING_OWNER_INPUT_REQUIRED,
    OP_CREATE_CANONICAL,
    OP_OWNER_INPUT,
    CompatibilityFinding,
    CompatibilitySnapshot,
    MigrationOperation,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.services.workspace_migration_registry import MigrationTransition
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.project_verticals import (
    ProjectVerticalService,
    project_definition_state_from_payload,
)


SEMANTIC_AUDIT_TIMESTAMP = "__P2P_APPLY_AT__"
SEMANTIC_AUDIT_ACTOR = "__P2P_ACTOR__"
PLAN_FINGERPRINT_PLACEHOLDER = "__P2P_PLAN_FINGERPRINT__"


@dataclass(frozen=True)
class TransitionPlanFragment:
    migration_id: str
    operations: tuple[MigrationOperation, ...]
    candidate_files: Mapping[str, bytes]
    findings: tuple[CompatibilityFinding, ...] = ()
    required_owner_inputs: tuple[str, ...] = ()
    validators: tuple[str, ...] = ()
    owned_candidate_targets: tuple[str, ...] = ()
    applicable: bool = True


class WorkspaceMigrationTransitionHandler(Protocol):
    transition: MigrationTransition
    planner_key: str
    owned_candidate_targets: tuple[str, ...]
    validators: tuple[str, ...]

    def plan(
        self,
        *,
        context: Any,
        snapshot: CompatibilitySnapshot,
        findings: Sequence[CompatibilityFinding],
        owner_inputs: Mapping[str, object],
        applicable: bool,
        candidate_view: Any,
        base_plan: Any | None = None,
    ) -> TransitionPlanFragment: ...

    def validate_candidate_targets(self, targets: Sequence[str]) -> None: ...


@dataclass(frozen=True)
class RegisteredWorkspaceMigrationHandler:
    transition: MigrationTransition
    planner_key: str
    owned_candidate_targets: tuple[str, ...]
    validators: tuple[str, ...]
    allow_managed_prefixes: tuple[str, ...] = ()

    def validate_candidate_targets(self, targets: Sequence[str]) -> None:
        allowed = set(self.owned_candidate_targets)
        for target in targets:
            if target in allowed:
                continue
            if any(target.startswith(prefix) for prefix in self.allow_managed_prefixes):
                continue
            raise ValueError(
                f"Workspace migration handler `{self.transition.migration_id}` does not own `{target}`."
            )


class LegacyUndeclaredToV1Handler(RegisteredWorkspaceMigrationHandler):
    def __init__(self, transition: MigrationTransition) -> None:
        super().__init__(
            transition=transition,
            planner_key="legacy_to_v1",
            owned_candidate_targets=(
                ".p2p/project.yml",
                ".p2p/project/domain.yml",
                ".p2p/project/permissions.yml",
                ".p2p/project/vertical.yml",
                ".p2p/project/vertical.lock.yml",
                ".p2p/project/definition.yml",
                ".p2p/project/rubrics.yml",
                ".p2p/project/workspace-schema.yml",
            ),
            validators=(
                "WorkspaceSchemaService",
                "PermissionsService",
                "ProjectMetadataService",
                "ProjectVerticalService",
            ),
        )

    def plan(
        self,
        *,
        context: Any,
        snapshot: CompatibilitySnapshot,
        findings: Sequence[CompatibilityFinding],
        owner_inputs: Mapping[str, object],
        applicable: bool,
        candidate_view: Any,
        base_plan: Any | None = None,
    ) -> TransitionPlanFragment:
        if base_plan is not None:
            raise ValueError("Legacy-to-v1 handler cannot compose over a prior migration plan")
        candidate_files: dict[str, bytes] = {}
        operations: list[MigrationOperation] = []
        plan_findings = list(findings)
        migration_id = self.transition.migration_id
        project = context._captured_yaml(".p2p/project.yml")
        project_data = project.get("project") if isinstance(project, dict) else None
        domain = str(project_data.get("domain") or "") if isinstance(project_data, dict) else ""

        missing_inputs = context._required_owner_inputs(domain, owner_inputs)
        for input_name, message in missing_inputs:
            plan_findings.append(
                CompatibilityFinding(
                    code="P2P323_MIGRATION_OWNER_INPUT_REQUIRED",
                    classification=FINDING_OWNER_INPUT_REQUIRED,
                    message=message,
                    recovery_action=f"Supply owner input: {input_name}",
                    migration_id=migration_id,
                )
            )
            operations.append(
                MigrationOperation(
                    operation_id=f"owner-input-{input_name.replace('.', '-')}",
                    kind=OP_OWNER_INPUT,
                    target=input_name,
                    reason=message,
                    migration_id=migration_id,
                    write_class="chat_only",
                    canonical=False,
                    before_exists=False,
                    before_physical_sha256=None,
                    candidate_semantic_sha256=None,
                    validator="WorkspaceMigrationOwnerInput",
                    rollback="not applicable",
                    applicable=False,
                )
            )
            applicable = False

        context._plan_domain(snapshot, project, domain, migration_id, candidate_files, operations)
        try:
            context._plan_permissions(
                snapshot,
                project,
                owner_inputs,
                migration_id,
                candidate_files,
                operations,
            )
            context._plan_metadata(
                snapshot,
                project,
                owner_inputs,
                migration_id,
                candidate_files,
                operations,
            )
        except ValueError as exc:
            plan_findings.append(
                CompatibilityFinding(
                    code="P2P336_INVALID_BOOTSTRAP_CANDIDATE",
                    classification=FINDING_INVALID,
                    message=str(exc),
                    recovery_action="Correct permission or metadata owner inputs and re-plan.",
                    migration_id=migration_id,
                )
            )
            applicable = False
        if not context._plan_vertical(
            snapshot,
            owner_inputs,
            domain,
            migration_id,
            candidate_files,
            operations,
            plan_findings,
        ):
            applicable = False
        context._plan_unknown_preservation(snapshot, migration_id, operations)
        context._plan_derived_refresh(migration_id, operations)

        schema_payload = context._semantic_schema_payload(
            migration_id=migration_id,
            source_version=self.transition.source_version,
            target_version=self.transition.target_version,
        )
        schema_target = ".p2p/project/workspace-schema.yml"
        candidate_files[schema_target] = yaml_dump(schema_payload).encode("utf-8")
        operations.append(
            context._candidate_operation(
                snapshot,
                operation_id="create-workspace-schema",
                kind=OP_CREATE_CANONICAL,
                target=schema_target,
                reason="Declare the successful legacy-to-v1 workspace transition.",
                migration_id=migration_id,
                candidate=schema_payload,
                validator="WorkspaceSchemaService",
                dependencies=tuple(item.operation_id for item in operations if item.canonical),
            )
        )
        self.validate_candidate_targets(candidate_files)
        return TransitionPlanFragment(
            migration_id=migration_id,
            operations=tuple(operations),
            candidate_files=candidate_files,
            findings=tuple(plan_findings),
            required_owner_inputs=tuple(name for name, _ in missing_inputs),
            validators=self.validators,
            owned_candidate_targets=tuple(sorted(candidate_files)),
            applicable=applicable,
        )


class WorkspaceV1ToV2ProjectQuestionsHandler(RegisteredWorkspaceMigrationHandler):
    def __init__(self, transition: MigrationTransition) -> None:
        super().__init__(
            transition=transition,
            planner_key="v1_to_v2_project_questions",
            owned_candidate_targets=(
                ".p2p/project/questions.yml",
                ".p2p/project/definition.yml",
                ".p2p/project/workspace-schema.yml",
            ),
            validators=(
                "ProjectQuestionStateService",
                "ProjectVerticalService",
                "WorkspaceSchemaService",
            ),
        )

    def plan(
        self,
        *,
        context: Any,
        snapshot: CompatibilitySnapshot,
        findings: Sequence[CompatibilityFinding],
        owner_inputs: Mapping[str, object],
        applicable: bool,
        candidate_view: Any,
        base_plan: Any | None = None,
    ) -> TransitionPlanFragment:
        migration_id = self.transition.migration_id
        candidate_files = {
            path: content
            for path, content in (base_plan.candidate_files.items() if base_plan else ())
            if path != ".p2p/project/workspace-schema.yml"
        }
        operations = [
            operation
            for operation in (base_plan.operations if base_plan else ())
            if operation.target != ".p2p/project/workspace-schema.yml"
            and operation.operation_id != "refresh-derived-after-migration"
        ]
        plan_findings = list(findings)
        questions_target = ".p2p/project/questions.yml"
        definition_target = ".p2p/project/definition.yml"
        schema_target = ".p2p/project/workspace-schema.yml"
        owned_candidates: set[str] = set()

        if self._overlay_content(candidate_view, questions_target) is not None:
            plan_findings.append(
                CompatibilityFinding(
                    code="P2P351_PROJECT_QUESTION_AUTHORITY_CONFLICT",
                    classification=FINDING_INVALID,
                    message=(
                        "Schema v1 workspace already contains project question state "
                        "outside migration authority."
                    ),
                    path=questions_target,
                    recovery_action=(
                        "Remove or classify the conflicting artifact through an owning "
                        "migration primitive."
                    ),
                    migration_id=migration_id,
                )
            )
            applicable = False

        definition_content = self._overlay_content(candidate_view, definition_target)
        project_questions: bytes
        migrated_count = 0
        if definition_content is None:
            question_service = ProjectQuestionStateService(root=context.root, p2p_dir=context.p2p_dir)
            artifact = question_service.empty_artifact(
                project_id=snapshot.project_id or "project",
                vertical_id="unselected",
                vertical_version="0",
                lock_checksum="unlocked",
                actor=SEMANTIC_AUDIT_ACTOR,
                audit_at=SEMANTIC_AUDIT_TIMESTAMP,
            )
            project_questions = question_service.candidate_bytes(artifact)
        else:
            try:
                definition_payload = yaml.safe_load(definition_content.decode("utf-8"))
                if not isinstance(definition_payload, dict):
                    raise ValueError("Project definition candidate must be a YAML mapping")
                definition_state = project_definition_state_from_payload(
                    definition_payload,
                    path=Path(definition_target),
                )
                vertical_service = ProjectVerticalService(
                    root=context.root,
                    p2p_dir=context.p2p_dir,
                    proposal_summaries=lambda: [],
                    find_proposal_dir=lambda proposal_id: context.p2p_dir / "proposals" / proposal_id,
                )
                pack = vertical_service.show_vertical(definition_state.vertical_id)
                definition_section_ids = {item.section_id for item in definition_state.sections}
                missing_required_sections = sorted(
                    item.section_id
                    for item in pack.sections
                    if item.required and item.section_id not in definition_section_ids
                )
                if missing_required_sections:
                    raise ValueError(
                        "Project definition candidate is missing required sections: "
                        + ", ".join(missing_required_sections)
                    )
                vertical_service.validate_definition_state(definition_state, pack)
                question_service = ProjectQuestionStateService(
                    root=context.root,
                    p2p_dir=context.p2p_dir,
                )
                seeded = question_service.seed_from_definition(
                    project_id=snapshot.project_id or "project",
                    definition=definition_state,
                    pack=pack,
                    lock_checksum=definition_state.lock_checksum or "unlocked",
                    actor=SEMANTIC_AUDIT_ACTOR,
                    audit_at=SEMANTIC_AUDIT_TIMESTAMP,
                    legacy_bindings=self._legacy_question_bindings(owner_inputs),
                )
                migrated_count = seeded.migrated_count
                project_questions = question_service.candidate_bytes(seeded.artifact)
                for diagnostic in seeded.diagnostics:
                    plan_findings.append(
                        CompatibilityFinding(
                            code=diagnostic.code,
                            classification=FINDING_DEGRADED,
                            message=diagnostic.message,
                            path=definition_target,
                            recovery_action=diagnostic.suggested_command,
                            migration_id=migration_id,
                        )
                    )
                normalized_definition = self._normalize_definition_questions(definition_payload)
                normalized_bytes = yaml_dump(normalized_definition).encode("utf-8")
                if normalized_bytes != definition_content:
                    operations = [
                        operation for operation in operations if operation.target != definition_target
                    ]
                    candidate_files[definition_target] = normalized_bytes
                    owned_candidates.add(definition_target)
                    operations.append(
                        context._candidate_operation(
                            snapshot,
                            operation_id="normalize-project-definition-questions",
                            kind="update_canonical",
                            target=definition_target,
                            reason="Move legacy project questions to the schema-v2 authority artifact.",
                            migration_id=migration_id,
                            candidate=normalized_definition,
                            validator="ProjectVerticalService+ProjectQuestionStateService",
                        )
                    )
            except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
                message = str(exc)
                ambiguous_binding = "P2P350_AMBIGUOUS_LEGACY_QUESTION" in message
                plan_findings.append(
                    CompatibilityFinding(
                        code=(
                            "P2P350_AMBIGUOUS_LEGACY_QUESTION"
                            if ambiguous_binding
                            else "P2P340_PROJECT_QUESTIONS_INVALID"
                        ),
                        classification=(
                            FINDING_OWNER_INPUT_REQUIRED if ambiguous_binding else FINDING_INVALID
                        ),
                        message=message,
                        path=definition_target,
                        recovery_action=(
                            "Supply an explicit legacy question target binding and re-plan."
                            if ambiguous_binding
                            else "Repair the legacy project definition through its owning primitive and re-plan."
                        ),
                        migration_id=migration_id,
                    )
                )
                applicable = False
                project_questions = b""

        if project_questions:
            question_payload = yaml.safe_load(project_questions.decode("utf-8"))
            candidate_files[questions_target] = project_questions
            owned_candidates.add(questions_target)
            operations.append(
                context._candidate_operation(
                    snapshot,
                    operation_id="create-project-question-state",
                    kind=OP_CREATE_CANONICAL,
                    target=questions_target,
                    reason=(
                        "Create schema-v2 project question state and preserve "
                        f"{migrated_count} legacy questions exactly once."
                    ),
                    migration_id=migration_id,
                    candidate=question_payload,
                    validator="ProjectQuestionStateService",
                )
            )

        try:
            schema_payload = self._schema_payload(candidate_view=candidate_view, base_plan=base_plan)
        except ValueError as exc:
            plan_findings.append(
                CompatibilityFinding(
                    code="P2P302_WORKSPACE_SCHEMA_INVALID",
                    classification=FINDING_INVALID,
                    message=str(exc),
                    path=schema_target,
                    migration_id=migration_id,
                )
            )
            applicable = False
            schema_payload = {}
        if schema_payload:
            candidate_files[schema_target] = yaml_dump(schema_payload).encode("utf-8")
            owned_candidates.add(schema_target)
            operations.append(
                context._candidate_operation(
                    snapshot,
                    operation_id="upgrade-workspace-schema-v2",
                    kind="update_canonical",
                    target=schema_target,
                    reason=(
                        "Commit workspace schema v2 after question and definition "
                        "candidates validate."
                    ),
                    migration_id=migration_id,
                    candidate=schema_payload,
                    validator="WorkspaceSchemaService",
                    dependencies=tuple(item.operation_id for item in operations if item.canonical),
                )
            )
        if base_plan is None:
            context._plan_unknown_preservation(snapshot, migration_id, operations)
        context._plan_derived_refresh(migration_id, operations)
        candidate_view.assert_owned_reads_used_candidates()
        self.validate_candidate_targets(sorted(owned_candidates))
        return TransitionPlanFragment(
            migration_id=migration_id,
            operations=tuple(operations),
            candidate_files=candidate_files,
            findings=tuple(plan_findings),
            validators=self.validators,
            owned_candidate_targets=tuple(sorted(owned_candidates)),
            applicable=applicable,
        )

    @staticmethod
    def _overlay_content(candidate_view: Any, target: str) -> bytes | None:
        try:
            return candidate_view.read_bytes(target)
        except FileNotFoundError:
            return None

    def _schema_payload(self, *, candidate_view: Any, base_plan: Any | None) -> dict[str, object]:
        target = ".p2p/project/workspace-schema.yml"
        schema_content = self._overlay_content(candidate_view, target)
        if schema_content is None:
            raise ValueError("Workspace schema v1 source is missing")
        try:
            payload = yaml.safe_load(schema_content.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Cannot parse workspace schema v1 source: {exc}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("workspace_schema"), dict):
            raise ValueError("Workspace schema v1 source is invalid")
        raw = dict(payload["workspace_schema"])
        history = list(raw.get("applied_migrations") or [])
        history.append(
            {
                "id": self.transition.migration_id,
                "from": self.transition.source_version,
                "to": self.transition.target_version,
                "applied_at": SEMANTIC_AUDIT_TIMESTAMP,
                "actor": SEMANTIC_AUDIT_ACTOR,
                "plan_fingerprint_sha256": PLAN_FINGERPRINT_PLACEHOLDER,
            }
        )
        raw["current_version"] = self.transition.target_version
        raw["baseline"] = "migrated_legacy" if base_plan else "migrated_declared"
        raw["applied_migrations"] = history
        return {"workspace_schema": raw}

    @staticmethod
    def _normalize_definition_questions(payload: Mapping[str, object]) -> dict[str, object]:
        normalized = dict(payload)
        raw = payload.get("project_definition")
        if not isinstance(raw, Mapping):
            raise ValueError("Project definition candidate requires project_definition mapping")
        definition = dict(raw)
        sections = definition.get("sections")
        if not isinstance(sections, list):
            raise ValueError("Project definition candidate requires sections sequence")
        normalized_sections: list[object] = []
        for item in sections:
            if not isinstance(item, Mapping):
                raise ValueError("Project definition section must be a mapping")
            section = dict(item)
            section["open_questions"] = []
            normalized_sections.append(section)
        definition["sections"] = normalized_sections
        normalized["project_definition"] = definition
        return normalized

    @staticmethod
    def _legacy_question_bindings(
        owner_inputs: Mapping[str, object],
    ) -> Mapping[str, Mapping[str, object]]:
        project_questions = owner_inputs.get("project_questions")
        if not isinstance(project_questions, Mapping):
            return {}
        bindings = project_questions.get("legacy_bindings")
        if not isinstance(bindings, Mapping):
            return {}
        return {
            str(key): value
            for key, value in bindings.items()
            if isinstance(value, Mapping)
        }
