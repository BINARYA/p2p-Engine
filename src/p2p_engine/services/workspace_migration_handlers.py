from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
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
from p2p_engine.foundation.files import identity_slug, yaml_dump
from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAffectedDecision,
    ProposalDecisionAuthorityEvidence,
    ProposalDecisionAuthorityResolution,
    ProposalDecisionCondition,
    ProposalDecisionEffectiveState,
    ProposalDecisionEventType,
    ProposalDecisionImpactBinding,
    ProposalDecisionLedger,
    ProposalDecisionMigrationProvenance,
    ProposalDecisionReadinessBinding,
)
from p2p_engine.services.proposal_decision_legacy import ProposalDecisionLegacyAdapter
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    decision_semantic_sha256,
    operation_key,
    proposal_semantic_sha256,
    render_decision_projection,
    render_proposal_projection,
)
from p2p_engine.services.permissions import PermissionsService
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


class WorkspaceV2ToV3ProposalDecisionLedgerHandler(RegisteredWorkspaceMigrationHandler):
    def __init__(self, transition: MigrationTransition) -> None:
        super().__init__(
            transition=transition,
            planner_key="v2_to_v3_proposal_decision_ledgers",
            owned_candidate_targets=(".p2p/project/workspace-schema.yml",),
            allow_managed_prefixes=(".p2p/proposals/",),
            validators=(
                "ProposalDecisionLedgerCodec",
                "ProposalLifecycleAuthorityService",
                "WorkspaceSchemaService",
            ),
        )
        object.__setattr__(self, "codec", ProposalDecisionLedgerCodec())
        object.__setattr__(self, "legacy", ProposalDecisionLegacyAdapter())

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
        schema_target = ".p2p/project/workspace-schema.yml"
        candidate_files = {
            path: content
            for path, content in (base_plan.candidate_files.items() if base_plan else ())
            if path != schema_target
        }
        operations = [
            operation
            for operation in (base_plan.operations if base_plan else ())
            if operation.target != schema_target
            and operation.operation_id != "refresh-derived-after-migration"
        ]
        plan_findings = list(findings)
        owned_candidates: set[str] = set()
        proposal_sources = self._proposal_sources(snapshot, candidate_files)
        permission_payload = self._overlay_yaml(
            candidate_view,
            ".p2p/project/permissions.yml",
        )
        permission_sha256 = semantic_sha256(permission_payload)
        attestations = self._authority_attestations(owner_inputs)
        seen_ids: set[str] = set()

        for proposal_id, proposal_dir in proposal_sources:
            if proposal_id in seen_ids:
                plan_findings.append(
                    CompatibilityFinding(
                        code="P2P361_DECISION_LEDGER_INVALID",
                        classification=FINDING_INVALID,
                        message=f"Duplicate proposal identity `{proposal_id}` blocks ledger migration.",
                        path=proposal_dir,
                        recovery_action="Repair duplicate proposal directories through an owning primitive.",
                        migration_id=migration_id,
                    )
                )
                applicable = False
                continue
            seen_ids.add(proposal_id)
            proposal_target = f"{proposal_dir}/proposal.md"
            decision_target = f"{proposal_dir}/decision.md"
            ledger_target = f"{proposal_dir}/decision-events.yml"
            try:
                proposal_bytes = candidate_view.read_bytes(proposal_target)
            except FileNotFoundError:
                plan_findings.append(
                    CompatibilityFinding(
                        code="P2P361_DECISION_LEDGER_INVALID",
                        classification=FINDING_INVALID,
                        message=f"{proposal_id} has no readable proposal.md source.",
                        path=proposal_target,
                        recovery_action="Repair the proposal source before migration.",
                        migration_id=migration_id,
                    )
                )
                applicable = False
                continue
            try:
                proposal_text = proposal_bytes.decode("utf-8")
            except UnicodeDecodeError:
                plan_findings.append(
                    CompatibilityFinding(
                        code="P2P361_DECISION_LEDGER_INVALID",
                        classification=FINDING_INVALID,
                        message=f"{proposal_id} proposal.md is not UTF-8.",
                        path=proposal_target,
                        recovery_action="Repair the proposal source before migration.",
                        migration_id=migration_id,
                    )
                )
                applicable = False
                continue
            try:
                decision_bytes = candidate_view.read_bytes(decision_target)
            except FileNotFoundError:
                decision_bytes = None
            snapshot_value = self.legacy.capture_bytes(
                proposal_id=proposal_id,
                proposal_path=proposal_target,
                decision_path=decision_target,
                proposal_bytes=proposal_bytes,
                decision_bytes=decision_bytes,
            )
            try:
                ledger = self._ledger_candidate(
                    snapshot_value,
                    proposal_text=proposal_text,
                    permission_payload=permission_payload,
                    permission_sha256=permission_sha256,
                    migration_id=migration_id,
                    attestation=attestations.get(proposal_id),
                )
            except ValueError as exc:
                plan_findings.append(
                    CompatibilityFinding(
                        code="P2P390_MIGRATION_ATTESTATION_INVALID",
                        classification=FINDING_INVALID,
                        message=str(exc),
                        path=ledger_target,
                        recovery_action=(
                            "Regenerate the read-only attestation template, review "
                            "the exact legacy sources and re-plan with a corrected input."
                        ),
                        migration_id=migration_id,
                    )
                )
                applicable = False
                ledger = self._unknown_legacy_ledger(
                    snapshot_value,
                    migration_id=migration_id,
                )
            if (
                ledger.authority_resolution
                == ProposalDecisionAuthorityResolution.unknown_legacy
            ):
                plan_findings.append(
                    CompatibilityFinding(
                        code="P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED",
                        classification=FINDING_DEGRADED,
                        message=(
                            f"{proposal_id} legacy authority is preserved but requires "
                            "owner resolution before a later decision event."
                        ),
                        path=ledger_target,
                        recovery_action=(
                            f"After migration run `p2p decision legacy-resolution preview {proposal_id}`."
                        ),
                        migration_id=migration_id,
                    )
                )
            ledger_bytes = self.codec.dumps(ledger)
            projected_proposal = render_proposal_projection(
                proposal_text,
                ledger.effective_state,
            ).encode("utf-8")
            projected_decision = render_decision_projection(
                proposal_id,
                ledger.events[-1] if ledger.events else None,
                empty_state=ledger.effective_state,
            ).encode("utf-8")
            candidates = (
                (ledger_target, ledger_bytes, "create-proposal-decision-ledger"),
                (proposal_target, projected_proposal, "normalize-proposal-decision-status"),
                (decision_target, projected_decision, "normalize-decision-projection"),
            )
            for target, content, operation_prefix in candidates:
                existing = self._overlay_bytes(candidate_view, target)
                candidate_files[target] = content
                owned_candidates.add(target)
                candidate_value: object
                if target.endswith((".yml", ".yaml")):
                    candidate_value = yaml.safe_load(content.decode("utf-8"))
                else:
                    candidate_value = content.decode("utf-8")
                operations.append(
                    context._candidate_operation(
                        snapshot,
                        operation_id=f"{operation_prefix}-{proposal_id.lower()}",
                        kind=(
                            OP_CREATE_CANONICAL
                            if existing is None
                            else "update_canonical"
                        ),
                        target=target,
                        reason=(
                            "Materialize schema-v3 proposal decision authority and "
                            "matching engine-owned projections."
                        ),
                        migration_id=migration_id,
                        candidate=candidate_value,
                        validator="ProposalDecisionLedgerCodec+ProposalLifecycleAuthorityService",
                    )
                )

        for proposal_id in sorted(set(attestations) - seen_ids):
            plan_findings.append(
                CompatibilityFinding(
                    code="P2P390_MIGRATION_ATTESTATION_INVALID",
                    classification=FINDING_INVALID,
                    message=(
                        f"Attestation references proposal `{proposal_id}`, which is "
                        "not present in the migration source set."
                    ),
                    path=".p2p/proposals",
                    recovery_action=(
                        "Regenerate the read-only attestation template and remove "
                        "stale proposal entries."
                    ),
                    migration_id=migration_id,
                )
            )
            applicable = False

        try:
            schema_payload = self._schema_payload(
                candidate_view=candidate_view,
                base_plan=base_plan,
            )
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
            schema_payload = {}
            applicable = False
        if schema_payload:
            candidate_files[schema_target] = yaml_dump(schema_payload).encode("utf-8")
            owned_candidates.add(schema_target)
            operations.append(
                context._candidate_operation(
                    snapshot,
                    operation_id="upgrade-workspace-schema-v3",
                    kind="update_canonical",
                    target=schema_target,
                    reason=(
                        "Commit workspace schema v3 after every proposal ledger and "
                        "projection candidate validates."
                    ),
                    migration_id=migration_id,
                    candidate=schema_payload,
                    validator="WorkspaceSchemaService+ProposalDecisionLedgerCodec",
                    dependencies=tuple(
                        item.operation_id for item in operations if item.canonical
                    ),
                )
            )
        context._plan_derived_refresh(migration_id, operations)
        self.validate_candidate_targets(sorted(owned_candidates))
        return TransitionPlanFragment(
            migration_id=migration_id,
            operations=tuple(operations),
            candidate_files=candidate_files,
            findings=tuple(plan_findings),
            required_owner_inputs=(),
            validators=self.validators,
            owned_candidate_targets=tuple(sorted(owned_candidates)),
            applicable=applicable,
        )

    def _ledger_candidate(
        self,
        snapshot: Any,
        *,
        proposal_text: str,
        permission_payload: Mapping[str, object],
        permission_sha256: str,
        migration_id: str,
        attestation: Mapping[str, object] | None,
    ) -> ProposalDecisionLedger:
        if snapshot.normalized_state == "undecided":
            if attestation is not None:
                raise ValueError(
                    f"{snapshot.proposal_id} is undecided and cannot be attested "
                    "as a historical decision."
                )
            return self.codec.empty(snapshot.proposal_id)
        event_type = self._migratable_event(snapshot, permission_payload)
        attested = False
        authority_owner = snapshot.approver
        authority_kind = "person"
        conditions: tuple[ProposalDecisionCondition, ...] = ()
        if event_type is not None and attestation is not None:
            raise ValueError(
                f"{snapshot.proposal_id} already has owner-resolved legacy authority; "
                "an attestation is not applicable."
            )
        if event_type is None and attestation is None:
            return self._unknown_legacy_ledger(
                snapshot,
                migration_id=migration_id,
            )
        if event_type is None:
            assert attestation is not None
            event_type, authority_owner, authority_kind, conditions = (
                self._validate_attestation(
                    snapshot,
                    permission_payload=permission_payload,
                    attestation=attestation,
                )
            )
            attested = True
        proposal_sha = proposal_semantic_sha256(snapshot.proposal_id, proposal_text)
        effective_state = ProposalDecisionEffectiveState(event_type.value)
        decision_sha = decision_semantic_sha256(
            proposal_sha256=proposal_sha,
            outcome=effective_state,
            rationale=snapshot.reason,
            conditions=conditions,
        )
        source_sha256 = {
            "proposal.md": hashlib.sha256(snapshot.proposal_bytes or b"").hexdigest(),
        }
        if snapshot.decision_bytes is not None:
            source_sha256["decision.md"] = hashlib.sha256(
                snapshot.decision_bytes
            ).hexdigest()
        preserved_values = {
            "proposal_status": snapshot.proposal_status,
            "decision_status": snapshot.decision_status,
            "outcome": snapshot.outcome,
            "reason": snapshot.reason,
            "approver": snapshot.approver,
            "decided_on": snapshot.decided_on,
        }
        if attested:
            assert attestation is not None
            preserved_values["owner_attestation"] = {
                "attestation_contract_version": 1,
                "owner_id": authority_owner,
                "legacy_status": snapshot.proposal_status,
                "legacy_approver": snapshot.approver,
                "decided_on": snapshot.decided_on,
                "source_sha256": source_sha256,
            }
        migration = ProposalDecisionMigrationProvenance(
            migration_id=migration_id,
            source_paths=(snapshot.proposal_path, snapshot.decision_path),
            source_sha256=source_sha256,
            preserved_values=preserved_values,
        )
        request_semantics = {
            "migration_id": migration_id,
            "proposal_id": snapshot.proposal_id,
            "event_type": event_type.value,
            "decision_semantic_sha256": decision_sha,
            "source_sha256": source_sha256,
        }
        if attested:
            request_semantics["owner_attestation"] = preserved_values[
                "owner_attestation"
            ]
        preview_token = semantic_sha256(
            {"migration_preview": request_semantics}
        )
        request_sha256 = semantic_sha256(request_semantics)
        event = self.codec.build_event(
            proposal_id=snapshot.proposal_id,
            event_type=event_type,
            effective_state=effective_state,
            rationale=snapshot.reason,
            conditions=conditions,
            decided_on=snapshot.decided_on,
            authority=ProposalDecisionAuthorityEvidence(
                owner_id=authority_owner,
                owner_role="owner",
                executor_actor_id=authority_owner,
                executor_kind=authority_kind,
                channel=(
                    "workspace_migration_owner_attestation"
                    if attested
                    else "workspace_migration"
                ),
                permission_policy_sha256=permission_sha256,
            ),
            predecessor=None,
            proposal_semantic_sha256=proposal_sha,
            decision_semantic_sha256=decision_sha,
            affected_decision=ProposalDecisionAffectedDecision(),
            lineage=self._empty_lineage(),
            impact=ProposalDecisionImpactBinding(),
            readiness=ProposalDecisionReadinessBinding(),
            preview_token=preview_token,
            request_fingerprint_sha256=request_sha256,
            operation_key=operation_key(request_semantics, None),
            migration=migration,
        )
        return self.codec.append(self.codec.empty(snapshot.proposal_id), event)

    def _validate_attestation(
        self,
        snapshot: Any,
        *,
        permission_payload: Mapping[str, object],
        attestation: Mapping[str, object],
    ) -> tuple[
        ProposalDecisionEventType,
        str,
        str,
        tuple[ProposalDecisionCondition, ...],
    ]:
        if not snapshot.aligned or not snapshot.authority_fields_complete:
            raise ValueError(
                f"{snapshot.proposal_id} legacy sources are divergent or incomplete."
            )
        status = str(attestation.get("legacy_status") or "")
        if status != snapshot.proposal_status:
            raise ValueError(
                f"{snapshot.proposal_id} legacy status changed after attestation."
            )
        if str(attestation.get("legacy_approver") or "") != snapshot.approver:
            raise ValueError(
                f"{snapshot.proposal_id} legacy approver changed after attestation."
            )
        if str(attestation.get("decided_on") or "") != snapshot.decided_on:
            raise ValueError(
                f"{snapshot.proposal_id} decision date changed after attestation."
            )
        actual_hashes = {
            "proposal.md": hashlib.sha256(snapshot.proposal_bytes or b"").hexdigest(),
            "decision.md": hashlib.sha256(snapshot.decision_bytes or b"").hexdigest(),
        }
        supplied_hashes = attestation.get("source_sha256")
        if not isinstance(supplied_hashes, Mapping) or dict(supplied_hashes) != actual_hashes:
            raise ValueError(
                f"{snapshot.proposal_id} source hashes changed after attestation."
            )

        owner_id = str(attestation.get("owner_id") or "")
        identities = permission_payload.get("identities")
        identity = (
            identities.get(identity_slug(owner_id))
            if isinstance(identities, Mapping)
            else None
        )
        if not isinstance(identity, Mapping) or str(identity.get("role") or "") != "owner":
            raise ValueError(
                f"{snapshot.proposal_id} attesting actor `{owner_id}` is not a "
                "current project owner."
            )
        actor_kind = str(identity.get("kind") or "")
        if actor_kind not in {"person", "agent", "client"}:
            raise ValueError(
                f"{snapshot.proposal_id} attesting owner has an invalid actor kind."
            )
        raw_conditions = attestation.get("conditions")
        conditions = tuple(
            ProposalDecisionCondition(
                condition_id=str(item["id"]),
                text=str(item["text"]),
            )
            for item in (raw_conditions if isinstance(raw_conditions, list) else ())
            if isinstance(item, Mapping)
        )
        return (
            ProposalDecisionEventType(status),
            identity_slug(owner_id),
            actor_kind,
            conditions,
        )

    def _unknown_legacy_ledger(
        self,
        snapshot: Any,
        *,
        migration_id: str,
    ) -> ProposalDecisionLedger:
        return ProposalDecisionLedger(
            contract_version=1,
            proposal_id=snapshot.proposal_id,
            authority_resolution=ProposalDecisionAuthorityResolution.unknown_legacy,
            effective_state=ProposalDecisionEffectiveState.unknown_legacy,
            head_event_id=None,
            legacy_evidence=(
                self.legacy.legacy_evidence(snapshot, migration_id=migration_id),
            ),
        )

    @staticmethod
    def _authority_attestations(
        owner_inputs: Mapping[str, object],
    ) -> Mapping[str, Mapping[str, object]]:
        proposal_decisions = owner_inputs.get("proposal_decisions")
        if not isinstance(proposal_decisions, Mapping):
            return {}
        values = proposal_decisions.get("authority_attestations")
        if not isinstance(values, Mapping):
            return {}
        return {
            str(proposal_id): attestation
            for proposal_id, attestation in values.items()
            if isinstance(attestation, Mapping)
        }

    def _migratable_event(
        self,
        snapshot: Any,
        permission_payload: Mapping[str, object],
    ) -> ProposalDecisionEventType | None:
        if not snapshot.aligned or not snapshot.authority_fields_complete:
            return None
        try:
            date.fromisoformat(snapshot.decided_on)
        except ValueError:
            return None
        if snapshot.proposal_status not in {
            "accepted",
            "deferred",
            "withdrawn",
            "rejected",
        }:
            return None
        identities = permission_payload.get("identities")
        identity = (
            identities.get(identity_slug(snapshot.approver))
            if isinstance(identities, Mapping)
            else None
        )
        if not isinstance(identity, Mapping):
            return None
        if str(identity.get("role") or "") != "owner":
            return None
        return ProposalDecisionEventType(snapshot.proposal_status)

    @staticmethod
    def _empty_lineage():
        from p2p_engine.core.proposal_decision_events import ProposalDecisionLineage

        return ProposalDecisionLineage()

    def _proposal_sources(
        self,
        snapshot: CompatibilitySnapshot,
        candidates: Mapping[str, bytes],
    ) -> tuple[tuple[str, str], ...]:
        directories: set[str] = set()
        for path in [
            *(item.path for item in snapshot.inventory),
            *candidates,
        ]:
            if not path.startswith(".p2p/proposals/") or not path.endswith("/proposal.md"):
                continue
            directories.add(path.rsplit("/", 1)[0])
        result: list[tuple[str, str]] = []
        for directory in sorted(directories):
            name = directory.rsplit("/", 1)[-1]
            parts = name.split("-", 2)
            if len(parts) < 2 or parts[0] != "PROP" or not parts[1].isdigit():
                continue
            result.append((f"PROP-{parts[1]}", directory))
        return tuple(result)

    @staticmethod
    def _overlay_bytes(candidate_view: Any, target: str) -> bytes | None:
        try:
            return candidate_view.read_bytes(target)
        except FileNotFoundError:
            return None

    @staticmethod
    def _overlay_yaml(candidate_view: Any, target: str) -> dict[str, object]:
        try:
            return candidate_view.read_yaml_mapping(target)
        except FileNotFoundError:
            return {}

    def _schema_payload(
        self,
        *,
        candidate_view: Any,
        base_plan: Any | None,
    ) -> dict[str, object]:
        target = ".p2p/project/workspace-schema.yml"
        content = self._overlay_bytes(candidate_view, target)
        if content is None:
            raise ValueError("Workspace schema v2 source is missing")
        try:
            payload = yaml.safe_load(content.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Cannot parse workspace schema v2 source: {exc}") from exc
        if not isinstance(payload, dict) or not isinstance(
            payload.get("workspace_schema"),
            dict,
        ):
            raise ValueError("Workspace schema v2 source is invalid")
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
