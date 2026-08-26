from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from p2p_engine.core.project_memory import MemoryClassificationSnapshot
from p2p_engine.core.project_structure import (
    PROJECT_STRUCTURE_CRITERION_EVALUATORS,
    ProjectStructure,
    StructureCriterion,
)
from p2p_engine.core.project_readiness import (
    PROJECT_READINESS_ALGORITHM_VERSION,
    PROJECT_READINESS_CONTRACT,
    PROJECT_READINESS_CURSOR_POLICY_VERSION,
    PROJECT_READINESS_DEFAULT_PAYLOAD_BYTES,
    PROJECT_READINESS_DEFAULT_PAGE_SIZE,
    PROJECT_READINESS_GAP_POLICY_VERSION,
    PROJECT_READINESS_MAX_PAGE_SIZE,
    ProjectReadinessAxis,
    ProjectReadinessCursor,
    ProjectReadinessCriterionSnapshot,
    ProjectReadinessDiagnostic,
    ProjectReadinessGap,
    ProjectReadinessGapKind,
    ProjectReadinessGapSeverity,
    ProjectReadinessPage,
    ProjectReadinessRatio,
    ProjectReadinessResult,
    ProjectReadinessSectionSnapshot,
    ProjectReadinessSnapshot,
    ProjectReadinessAssumptionSnapshot,
    ProjectReadinessQuestionSnapshot,
    readiness_class_rank,
    readiness_gap_identity,
    readiness_snapshot_identity,
)
from p2p_engine.core.vertical_memory import VerticalProjectMemoryView


class ProjectReadinessSnapshotBuilder:
    def build(
        self,
        *,
        workspace_schema_version: int,
        workspace_schema_state: str,
        vertical_id: str,
        vertical_version: str,
        vertical_lock_checksum: str,
        profile: str,
        modules: Sequence[str],
        source_hashes: dict[str, str],
        policy_versions: dict[str, int],
        definition_valid: bool,
        definition_exists: bool,
        fallback_used: bool,
        vertical_source: str,
        sections: Sequence[ProjectReadinessSectionSnapshot],
        unmapped_proposals: Sequence[str],
        owner_available: bool = True,
        diagnostics: Sequence[ProjectReadinessDiagnostic] = (),
    ) -> ProjectReadinessSnapshot:
        identity = readiness_snapshot_identity(
            workspace_schema_version=workspace_schema_version,
            workspace_schema_state=workspace_schema_state,
            vertical_id=vertical_id,
            vertical_version=vertical_version,
            vertical_lock_checksum=vertical_lock_checksum,
            profile=profile,
            modules=modules,
            source_hashes=source_hashes,
            policy_versions=policy_versions,
        )
        return ProjectReadinessSnapshot(
            identity=identity,
            definition_valid=definition_valid,
            definition_exists=definition_exists,
            fallback_used=fallback_used,
            vertical_source=vertical_source,
            sections=tuple(sections),
            unmapped_proposals=tuple(sorted(str(item) for item in unmapped_proposals)),
            owner_available=owner_available,
            diagnostics=tuple(diagnostics),
        )


def readiness_snapshot_from_vertical_memory(
    view: VerticalProjectMemoryView,
    *,
    workspace_schema_version: int,
    workspace_schema_state: str,
    owner_available: bool,
    unmapped_proposals: Sequence[str] | None = None,
) -> ProjectReadinessSnapshot:
    sections: list[ProjectReadinessSectionSnapshot] = []
    for section in view.sections:
        definition = section.definition
        assumptions = tuple(
            ProjectReadinessAssumptionSnapshot(
                assumption_id=str(item.get("id") or ""),
                status=str(item.get("status") or "to_validate"),
                field_id=str(item.get("field_id") or ""),
            )
            for item in definition.get("assumptions", ())
            if isinstance(item, Mapping)
        )
        questions = tuple(
            ProjectReadinessQuestionSnapshot(
                question_id=str(item.get("id") or ""),
                revision=int(item.get("revision") or 1),
                state=str(item.get("state") or "to_answer"),
                target_kind=str(
                    (item.get("target") or {}).get("kind")
                    if isinstance(item.get("target"), Mapping)
                    else "section"
                ),
                target_id=str(
                    (item.get("target") or {}).get("id")
                    if isinstance(item.get("target"), Mapping)
                    else section.section_id
                ),
                applicability=(
                    "applicable"
                    if str(item.get("applicability") or "active") == "active"
                    else str(item.get("applicability") or "")
                ),
            )
            for item in section.questions
        )
        declared = tuple(
            sorted(
                {
                    item.proposal_id
                    for item in (
                        *section.active_contributions,
                        *section.historical_contributions,
                    )
                }
            )
        )
        active = tuple(
            sorted({item.proposal_id for item in section.active_contributions})
        )
        sections.append(
            ProjectReadinessSectionSnapshot(
                section_id=section.section_id,
                title=section.title,
                required=section.required,
                priority=section.priority,
                definition_status=str(definition.get("status") or "not_initialized"),
                missing_required_fields=tuple(
                    str(item) for item in definition.get("missing_required_fields", ())
                ),
                assumptions=assumptions,
                open_blocker_ids=tuple(
                    sorted(
                        {
                            str(item.get("id") or "")
                            for item in definition.get("blockers", ())
                            if isinstance(item, Mapping)
                            and str(item.get("status") or "open") == "open"
                        }
                        | {
                            str(item.get("id") or "")
                            for item in section.conflicts
                            if str(item.get("kind") or "") == "conflict"
                            and str(item.get("status") or "") == "unresolved"
                        }
                    )
                ),
                declared_proposals=declared,
                active_declared_proposals=active,
                heuristic_proposals=tuple(
                    sorted(
                        {
                            str(item.get("proposal_id") or "")
                            for item in section.heuristic_suggestions
                            if str(item.get("proposal_id") or "")
                        }
                    )
                ),
                declared_questions=section.declared_questions,
                question_states=questions,
            )
        )
    diagnostics = tuple(
        ProjectReadinessDiagnostic(
            code=str(item.get("code") or "VERTICAL_MEMORY_DIAGNOSTIC"),
            severity=str(item.get("severity") or "warning"),
            message=str(item.get("message") or item),
            suggested_command=str(item.get("suggested_command") or "p2p project memory status"),
            section_id=str(item.get("section_id") or ""),
        )
        for item in view.diagnostics
    )
    definition_exists = view.definition_exists
    definition_valid = view.definition_valid and not any(
        item.severity == "error" for item in diagnostics
    )
    return ProjectReadinessSnapshotBuilder().build(
        workspace_schema_version=workspace_schema_version,
        workspace_schema_state=workspace_schema_state,
        vertical_id=view.vertical_id,
        vertical_version=view.vertical_version,
        vertical_lock_checksum=view.vertical_lock_checksum,
        profile=view.profile,
        modules=view.modules,
        source_hashes={"vertical_project_memory": view.source_fingerprint_sha256},
        policy_versions={
            "gap": PROJECT_READINESS_GAP_POLICY_VERSION,
            "snapshot": 1,
            "vertical_memory": 1,
        },
        definition_valid=definition_valid,
        definition_exists=definition_exists,
        fallback_used=view.fallback_used,
        vertical_source=view.vertical_source,
        sections=sections,
        unmapped_proposals=(
            tuple(unmapped_proposals)
            if unmapped_proposals is not None
            else tuple(
                str(item.get("proposal_id") or "")
                for item in view.unmapped_active_proposals
            )
        ),
        owner_available=owner_available,
        diagnostics=diagnostics,
    )


def unmapped_proposal_ids_from_vertical_memory(
    view: VerticalProjectMemoryView,
    proposal_ids: Iterable[str],
) -> tuple[str, ...]:
    declared = {
        contribution.proposal_id
        for section in view.sections
        for contribution in (
            *section.active_contributions,
            *section.historical_contributions,
        )
    }
    return tuple(sorted({str(item) for item in proposal_ids if str(item)} - declared))


class ProjectReadinessCompositionService:
    def compose(
        self,
        *,
        structure: ProjectStructure,
        definition_view: Any,
        memory_classification: MemoryClassificationSnapshot,
        vertical_memory: VerticalProjectMemoryView | None = None,
        workspace_schema_status: Any = None,
        owner_available: bool = True,
        requested_vertical_id: str | None = None,
    ) -> ProjectReadinessSnapshot:
        diagnostics: list[ProjectReadinessDiagnostic] = []
        definition_state = getattr(definition_view, "state", None)
        definition_exists = bool(getattr(definition_view, "exists", False))
        definition_valid = bool(getattr(definition_view, "valid", False))
        if not definition_exists:
            diagnostics.append(
                ProjectReadinessDiagnostic(
                    code="P2P_PROJECT_READINESS_DEFINITION_MISSING",
                    severity="warning",
                    message="Project definition state is missing; active criteria are unsatisfied.",
                    suggested_command="p2p project definition show",
                )
            )
        for issue in getattr(definition_view, "issues", ()) or ():
            diagnostics.append(
                ProjectReadinessDiagnostic(
                    code=str(getattr(issue, "code", "") or "P2P_PROJECT_READINESS_DEFINITION_DIAGNOSTIC"),
                    severity=str(getattr(issue, "severity", "warning") or "warning"),
                    message=str(getattr(issue, "message", "") or issue),
                    suggested_command="p2p project definition show",
                    section_id=_section_id_from_issue(getattr(issue, "field", "")),
                )
            )
        if definition_state is not None and int(getattr(definition_state, "structure_revision", 0) or 0) < structure.revision:
            diagnostics.append(
                ProjectReadinessDiagnostic(
                    code="P2P_PROJECT_READINESS_STALE_STRUCTURE",
                    severity="warning",
                    message="Project definition references an older project-structure revision.",
                    suggested_command="p2p project readiness questions reconcile-preview --actor <ACTOR>",
                )
            )
        if memory_classification.status not in {"complete", "incomplete"}:
            diagnostics.append(
                ProjectReadinessDiagnostic(
                    code="P2P_PROJECT_READINESS_MEMORY_CLASSIFICATION_" + memory_classification.status.upper(),
                    severity="warning" if memory_classification.status == "stale" else "error",
                    message=(
                        "Memory classification is a sibling readiness source and is "
                        f"{memory_classification.status}."
                    ),
                    suggested_command="p2p project memory classification --format json",
                )
            )
        diagnostics.extend(
            ProjectReadinessDiagnostic(
                code=str(item.get("code") or "P2P_PROJECT_READINESS_MEMORY_CLASSIFICATION_DIAGNOSTIC"),
                severity=str(item.get("severity") or "warning"),
                message=str(item.get("message") or item),
                suggested_command="p2p project memory classification --format json",
                section_id=str(item.get("section_id") or ""),
            )
            for item in memory_classification.diagnostics
            if isinstance(item, Mapping)
        )
        if requested_vertical_id:
            diagnostics.append(
                ProjectReadinessDiagnostic(
                    code="P2P_PROJECT_READINESS_STRUCTURE_SOURCE",
                    severity="info",
                    message=(
                        "Project readiness v2 ignores alternate vertical denominators "
                        "and uses the current ProjectStructure."
                    ),
                )
            )
        workspace_version = int(getattr(workspace_schema_status, "current_version", 0) or 0)
        workspace_state = str(getattr(workspace_schema_status, "state", "") or "unknown")
        if workspace_schema_status is not None and str(getattr(workspace_schema_status, "layout_status", "current")) != "current":
            diagnostics.append(
                ProjectReadinessDiagnostic(
                    code="P2P_PROJECT_READINESS_WORKSPACE_SCHEMA",
                    severity="error",
                    message="Workspace schema is not current.",
                    suggested_command="p2p workspace schema status --format json",
                )
            )
        active_sections = tuple(
            sorted(
                (item for item in structure.sections if item.lifecycle == "active"),
                key=lambda item: (item.order, item.section_id),
            )
        )
        active_section_ids = {item.section_id for item in active_sections}
        criteria_by_section: dict[str, list[StructureCriterion]] = {
            section.section_id: [] for section in active_sections
        }
        for criterion in sorted(
            (
                item
                for item in structure.criteria
                if item.lifecycle == "active"
                and item.enabled
                and item.section_id in active_section_ids
            ),
            key=lambda item: (item.section_id, item.order, item.criterion_id),
        ):
            if criterion.evaluation not in PROJECT_STRUCTURE_CRITERION_EVALUATORS:
                diagnostics.append(
                    ProjectReadinessDiagnostic(
                        code="P2P_PROJECT_READINESS_UNKNOWN_EVALUATOR",
                        severity="error",
                        message=f"Criterion `{criterion.criterion_id}` has an unsupported evaluator.",
                        section_id=criterion.section_id,
                    )
                )
                continue
            criteria_by_section.setdefault(criterion.section_id, []).append(criterion)

        definition_by_section = {
            str(getattr(item, "section_id", "")): item
            for item in (getattr(definition_state, "sections", ()) if definition_state is not None else ())
        }
        memory_by_section = {
            section.section_id: section
            for section in (vertical_memory.sections if vertical_memory is not None else ())
        }
        evidence_by_section = _classification_evidence_by_section(memory_classification)
        debt_ids = _classification_debt_ids(memory_classification)
        section_snapshots: list[ProjectReadinessSectionSnapshot] = []
        definition_numerator = 0.0
        definition_denominator = 0.0
        evidence_numerator = 0.0
        evidence_denominator = 0.0
        active_weight = 0.0
        not_applicable_weight = 0.0

        for section in active_sections:
            definition_section = definition_by_section.get(section.section_id)
            memory_section = memory_by_section.get(section.section_id)
            definition_status = (
                str(getattr(definition_section, "status", "") or "not_initialized")
                if definition_section is not None
                else "not_initialized"
            )
            evidence_ids = evidence_by_section.get(section.section_id, ())
            criteria: list[ProjectReadinessCriterionSnapshot] = []
            for criterion in criteria_by_section.get(section.section_id, ()):
                active_weight += criterion.weight
                status, reason = _criterion_status(
                    criterion,
                    definition_status=definition_status,
                    evidence_ids=evidence_ids,
                )
                criteria.append(
                    ProjectReadinessCriterionSnapshot(
                        criterion_id=criterion.criterion_id,
                        section_id=section.section_id,
                        title=criterion.title,
                        weight=criterion.weight,
                        evaluation=criterion.evaluation,
                        required=criterion.required,
                        status=status,
                        definition_status=definition_status,
                        evidence_item_ids=evidence_ids,
                        not_applicable_reason=reason,
                    )
                )
                if status == "not_applicable":
                    not_applicable_weight += criterion.weight
                    continue
                definition_denominator += criterion.weight
                evidence_denominator += criterion.weight
                if status == "satisfied":
                    definition_numerator += criterion.weight
                if evidence_ids:
                    evidence_numerator += criterion.weight
            section_applicable = sum(item.weight for item in criteria if item.applicable)
            section_satisfied = sum(item.weight for item in criteria if item.satisfied)
            section_evidence = sum(item.weight for item in criteria if item.applicable and item.evidence_item_ids)
            section_active = sum(item.weight for item in criteria)
            section_snapshots.append(
                ProjectReadinessSectionSnapshot(
                    section_id=section.section_id,
                    title=section.title,
                    required=section.required,
                    priority=section.order,
                    definition_status=definition_status,
                    missing_required_fields=_missing_required_fields(definition_section),
                    assumptions=_assumptions_from_definition(definition_section, memory_section),
                    open_blocker_ids=_blockers_from_definition(definition_section, memory_section),
                    declared_proposals=evidence_ids,
                    active_declared_proposals=evidence_ids,
                    heuristic_proposals=_heuristic_proposals(memory_section),
                    declared_questions=_declared_questions(memory_section),
                    question_states=_questions_from_memory(memory_section),
                    criteria=tuple(criteria),
                    active_weight=section_active,
                    applicable_weight=section_applicable,
                    satisfied_weight=section_satisfied,
                    evidence_weight=section_evidence,
                    definition_score=_score(section_satisfied, section_applicable),
                    evidence_score=_score(section_evidence, section_applicable),
                    readiness_status="not_configured" if section_applicable == 0 else "calculated",
                )
            )

        definition_axis = ProjectReadinessAxis(
            axis_id="definition_completeness",
            status=_axis_status(definition_denominator, diagnostics, memory_classification.status),
            ratio=ProjectReadinessRatio(
                numerator=definition_numerator,
                denominator=definition_denominator,
                score=_score(definition_numerator, definition_denominator),
                exclusions={"not_applicable_weight": not_applicable_weight},
            ),
            basis="active_project_structure_criteria",
        )
        evidence_axis = ProjectReadinessAxis(
            axis_id="declared_evidence_coverage",
            status=_axis_status(evidence_denominator, diagnostics, memory_classification.status),
            ratio=ProjectReadinessRatio(
                numerator=evidence_numerator,
                denominator=evidence_denominator,
                score=_score(evidence_numerator, evidence_denominator),
                exclusions={
                    "not_applicable_weight": not_applicable_weight,
                    "project_global_items": memory_classification.counts.get("project_global", 0),
                    "unassigned_items": memory_classification.counts.get("unassigned", 0),
                    "requires_reassignment_items": memory_classification.counts.get("requires_reassignment", 0),
                },
            ),
            basis="active_section_classified_project_memory",
        )
        status = _overall_status(
            definition_denominator,
            diagnostics,
            memory_classification.status,
        )
        identity = readiness_snapshot_identity(
            workspace_schema_version=workspace_version,
            workspace_schema_state=workspace_state,
            vertical_id=str(getattr(vertical_memory, "vertical_id", "") or structure.origin.identity),
            vertical_version=str(getattr(vertical_memory, "vertical_version", "") or "project-owned"),
            vertical_lock_checksum=str(getattr(vertical_memory, "vertical_lock_checksum", "") or ""),
            profile=str(getattr(definition_state, "profile", "") or getattr(vertical_memory, "profile", "") or "default"),
            modules=tuple(getattr(definition_state, "modules", ()) or getattr(vertical_memory, "modules", ()) or ()),
            source_hashes={
                "project_structure": structure.checksum,
                "project_memory": memory_classification.memory_revision,
                "memory_classification": memory_classification.memory_revision,
                **(
                    {"vertical_project_memory": vertical_memory.source_fingerprint_sha256}
                    if vertical_memory is not None
                    else {}
                ),
            },
            policy_versions={
                "gap": PROJECT_READINESS_GAP_POLICY_VERSION,
                "snapshot": 2,
                "algorithm": 2,
            },
            structure_id=structure.structure_id,
            structure_revision=structure.revision,
            structure_checksum=structure.checksum,
            memory_revision=memory_classification.memory_revision,
            algorithm_version=PROJECT_READINESS_ALGORITHM_VERSION,
            contract_version=PROJECT_READINESS_CONTRACT,
        )
        actions = _bounded_actions(status, debt_ids, diagnostics)
        return ProjectReadinessSnapshot(
            identity=identity,
            definition_valid=definition_valid,
            definition_exists=definition_exists,
            fallback_used=bool(getattr(vertical_memory, "fallback_used", False)),
            vertical_source="project_structure",
            sections=tuple(section_snapshots),
            unmapped_proposals=debt_ids,
            owner_available=owner_available,
            diagnostics=tuple(diagnostics),
            status=status,
            definition=definition_axis,
            evidence=evidence_axis,
            actions=actions,
            memory_classification_status=memory_classification.status,
        )


def _classification_evidence_by_section(
    snapshot: MemoryClassificationSnapshot,
) -> dict[str, tuple[str, ...]]:
    result: dict[str, list[str]] = {}
    for item in snapshot.items:
        if item.object_type != "proposal" or item.state != "section_classified":
            continue
        for section_id in item.active_section_ids:
            result.setdefault(section_id, []).append(item.object_id)
    return {
        section_id: tuple(sorted(dict.fromkeys(values)))
        for section_id, values in sorted(result.items())
    }


def _classification_debt_ids(snapshot: MemoryClassificationSnapshot) -> tuple[str, ...]:
    return tuple(
        sorted(
            item.object_id
            for item in snapshot.items
            if item.object_type == "proposal"
            and item.state in {"unassigned", "requires_reassignment"}
        )
    )


def _criterion_status(
    criterion: StructureCriterion,
    *,
    definition_status: str,
    evidence_ids: Sequence[str],
) -> tuple[str, str]:
    if definition_status == "not_applicable":
        return "not_applicable", "section_marked_not_applicable"
    if criterion.evaluation == "definition_status":
        return ("satisfied", "") if definition_status == "complete" else ("missing", "")
    if criterion.evaluation == "declared_evidence":
        return ("satisfied", "") if evidence_ids else ("missing", "")
    raise ValueError(
        f"P2P_PROJECT_READINESS_UNKNOWN_EVALUATOR: {criterion.evaluation}"
    )


def _score(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator * 100 / denominator, 2)


def _axis_status(
    denominator: float,
    diagnostics: Sequence[ProjectReadinessDiagnostic],
    classification_status: str,
) -> str:
    if denominator <= 0:
        return "not_configured"
    if any(item.severity == "error" for item in diagnostics):
        return "error"
    if classification_status == "stale" or any(item.code.endswith("_STALE_STRUCTURE") for item in diagnostics):
        return "stale"
    if any(item.severity == "warning" for item in diagnostics):
        return "partial"
    return "calculated"


def _overall_status(
    denominator: float,
    diagnostics: Sequence[ProjectReadinessDiagnostic],
    classification_status: str,
) -> str:
    return _axis_status(denominator, diagnostics, classification_status)


def _bounded_actions(
    status: str,
    debt_ids: Sequence[str],
    diagnostics: Sequence[ProjectReadinessDiagnostic],
) -> tuple[str, ...]:
    actions: list[str] = []
    if status == "not_configured":
        actions.append("p2p project structure show --format json")
    if debt_ids:
        actions.append("p2p project memory classification --format json")
    for diagnostic in diagnostics:
        if diagnostic.suggested_command:
            actions.append(diagnostic.suggested_command)
    if not actions:
        actions.append("p2p project readiness review")
    return tuple(dict.fromkeys(actions[:10]))


def _section_id_from_issue(field: object) -> str:
    text = str(field or "")
    if text.startswith("sections."):
        parts = text.split(".")
        if len(parts) > 1:
            return parts[1]
    return ""


def _missing_required_fields(definition_section: Any) -> tuple[str, ...]:
    if definition_section is None:
        return ()
    return tuple(str(item) for item in getattr(definition_section, "missing_required_fields", ()) or ())


def _assumptions_from_definition(
    definition_section: Any,
    memory_section: Any,
) -> tuple[ProjectReadinessAssumptionSnapshot, ...]:
    if definition_section is not None:
        return tuple(
            ProjectReadinessAssumptionSnapshot(
                assumption_id=str(getattr(item, "assumption_id", "") or ""),
                status=str(getattr(item, "status", "") or "to_validate"),
                field_id=str(getattr(item, "field_id", "") or ""),
            )
            for item in getattr(definition_section, "assumptions", ()) or ()
        )
    definition = getattr(memory_section, "definition", {}) if memory_section is not None else {}
    if not isinstance(definition, Mapping):
        return ()
    return tuple(
        ProjectReadinessAssumptionSnapshot(
            assumption_id=str(item.get("id") or ""),
            status=str(item.get("status") or "to_validate"),
            field_id=str(item.get("field_id") or ""),
        )
        for item in definition.get("assumptions", ())
        if isinstance(item, Mapping)
    )


def _blockers_from_definition(
    definition_section: Any,
    memory_section: Any,
) -> tuple[str, ...]:
    blockers: set[str] = set()
    if definition_section is not None:
        blockers.update(
            str(getattr(item, "blocker_id", "") or "")
            for item in getattr(definition_section, "blockers", ()) or ()
            if str(getattr(item, "status", "open") or "open") == "open"
        )
    definition = getattr(memory_section, "definition", {}) if memory_section is not None else {}
    if isinstance(definition, Mapping):
        blockers.update(
            str(item.get("id") or "")
            for item in definition.get("blockers", ())
            if isinstance(item, Mapping) and str(item.get("status") or "open") == "open"
        )
    for conflict in getattr(memory_section, "conflicts", ()) if memory_section is not None else ():
        if (
            isinstance(conflict, Mapping)
            and str(conflict.get("kind") or "") == "conflict"
            and str(conflict.get("status") or "") == "unresolved"
        ):
            blockers.add(str(conflict.get("id") or "conflict"))
    return tuple(sorted(item for item in blockers if item))


def _heuristic_proposals(memory_section: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(item.get("proposal_id") or "")
                for item in (
                    getattr(memory_section, "heuristic_suggestions", ())
                    if memory_section is not None
                    else ()
                )
                if isinstance(item, Mapping) and str(item.get("proposal_id") or "")
            }
        )
    )


def _declared_questions(memory_section: Any) -> tuple[str, ...]:
    if memory_section is None:
        return ()
    return tuple(str(item) for item in getattr(memory_section, "declared_questions", ()) or ())


def _questions_from_memory(memory_section: Any) -> tuple[ProjectReadinessQuestionSnapshot, ...]:
    if memory_section is None:
        return ()
    questions: list[ProjectReadinessQuestionSnapshot] = []
    for item in getattr(memory_section, "questions", ()) or ():
        if not isinstance(item, Mapping):
            continue
        target = item.get("target") if isinstance(item.get("target"), Mapping) else {}
        questions.append(
            ProjectReadinessQuestionSnapshot(
                question_id=str(item.get("id") or ""),
                revision=int(item.get("revision") or 1),
                state=str(item.get("state") or "to_answer"),
                target_kind=str(target.get("kind") or "section"),
                target_id=str(target.get("id") or getattr(memory_section, "section_id", "")),
                applicability=(
                    "applicable"
                    if str(item.get("applicability") or "active") == "active"
                    else str(item.get("applicability") or "")
                ),
            )
        )
    return tuple(sorted(questions, key=lambda item: item.question_id))


def _uses_readiness_v2(snapshot: ProjectReadinessSnapshot) -> bool:
    return (
        snapshot.definition is not None
        or snapshot.evidence is not None
        or any(section.criteria for section in snapshot.sections)
    )


class ProjectReadinessSourceAccess:
    def __init__(
        self,
        *,
        root: Path,
        reader: Callable[[Path], bytes] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.reader = reader or (lambda path: path.read_bytes())
        self._cache: dict[Path, bytes | None] = {}
        self._counts: Counter[str] = Counter()

    @property
    def counts(self) -> dict[str, int]:
        return dict(sorted(self._counts.items()))

    def read_optional(self, path: Path) -> bytes | None:
        resolved = path.resolve()
        if resolved in self._cache:
            return self._cache[resolved]
        if not resolved.exists():
            self._cache[resolved] = None
            return None
        content = self.reader(resolved)
        key = self._display_path(resolved)
        self._counts[key] += 1
        self._cache[resolved] = content
        return content

    def _display_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()


class ProjectReadinessGapService:
    def classify(self, snapshot: ProjectReadinessSnapshot) -> ProjectReadinessResult:
        gaps: list[ProjectReadinessGap] = []
        uses_v2 = _uses_readiness_v2(snapshot)
        has_applicable_criteria = (
            any(section.applicable_weight > 0 for section in snapshot.sections)
            if uses_v2
            else True
        )
        if snapshot.identity.workspace_schema_state == "invalid":
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.COMPATIBILITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="workspace_schema",
                    target_id="workspace_schema",
                    definition_status="not_applicable",
                    next_operation="p2p workspace schema status --format json",
                    rationale="Workspace schema state is invalid and cannot authorize convergence writes.",
                )
            )
        if not snapshot.owner_available:
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.AUTHORITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="permissions",
                    target_id="owner",
                    definition_status="not_applicable",
                    next_operation="p2p permissions show",
                    rationale="No project-declared owner is available for required owner decisions.",
                )
            )
        for diagnostic in snapshot.diagnostics:
            if diagnostic.severity != "error" or "LOCK" not in diagnostic.code:
                continue
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.INTEGRITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="vertical_lock",
                    target_id=diagnostic.code,
                    definition_status="not_applicable",
                    next_operation=diagnostic.suggested_command or "p2p project vertical lock show",
                    rationale=diagnostic.message,
                )
            )
        if has_applicable_criteria and (
            not snapshot.definition_exists or not snapshot.definition_valid
        ):
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.INTEGRITY_BLOCKER,
                    severity=ProjectReadinessGapSeverity.BLOCKER,
                    target_kind="project_definition",
                    target_id="project_definition",
                    definition_status="missing" if not snapshot.definition_exists else "invalid",
                    next_operation="p2p project definition show",
                    rationale=(
                        "Project definition state is missing."
                        if not snapshot.definition_exists
                        else "Project definition state is invalid."
                    ),
                )
            )

        for section in snapshot.sections:
            gaps.extend(self._section_gaps(snapshot, section))

        if snapshot.unmapped_proposals:
            gaps.append(
                self._gap(
                    snapshot,
                    section=None,
                    kind=ProjectReadinessGapKind.UNMAPPED_PROPOSAL_COVERAGE,
                    severity=ProjectReadinessGapSeverity.INFO,
                    target_kind="proposal_collection",
                    target_id="unmapped_proposals",
                    definition_status="not_applicable",
                    heuristic_suggestions=snapshot.unmapped_proposals,
                    next_operation="p2p project memory classification --format json",
                    rationale=(
                        f"{len(snapshot.unmapped_proposals)} active proposal memory items are "
                        "unassigned or require reassignment. This does not change the readiness score."
                    ),
                )
            )

        self._validate_gap_id_collisions(gaps)
        ordered = tuple(sorted(gaps, key=self.sort_key))
        counts = Counter(item.kind.value for item in ordered)
        counts["total"] = len(ordered)
        return ProjectReadinessResult(
            snapshot=snapshot.identity,
            gaps=ordered,
            diagnostics=snapshot.diagnostics,
            counts=dict(sorted(counts.items())),
            status=snapshot.status,
            definition=snapshot.definition,
            evidence=snapshot.evidence,
            sections=snapshot.sections,
            actions=snapshot.actions,
            contract_version=snapshot.contract_version,
        )

    def _section_gaps(
        self,
        snapshot: ProjectReadinessSnapshot,
        section: ProjectReadinessSectionSnapshot,
    ) -> list[ProjectReadinessGap]:
        gaps: list[ProjectReadinessGap] = []
        applicable = section.definition_status != "not_applicable"
        for question in section.question_states:
            if question.applicability != "applicable":
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.COMPATIBILITY_BLOCKER,
                        severity=ProjectReadinessGapSeverity.BLOCKER,
                        target_kind=question.target_kind,
                        target_id=question.target_id,
                        next_operation=(
                            "p2p project readiness questions reconcile-preview "
                            "--actor <ACTOR>"
                        ),
                        rationale=f"Question `{question.question_id}` is not compatible with the active vertical.",
                        question_id=question.question_id,
                        question_revision=question.revision,
                    )
                )
            elif question.state == "answered":
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.ANSWERED_NOT_APPLIED,
                        severity=ProjectReadinessGapSeverity.HIGH,
                        target_kind=question.target_kind,
                        target_id=question.target_id,
                        next_operation="p2p project readiness convergence preview",
                        rationale=f"Question `{question.question_id}` has owner evidence awaiting apply.",
                        question_id=question.question_id,
                        question_revision=question.revision,
                    )
                )
            elif question.state == "to_answer":
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION,
                        severity=ProjectReadinessGapSeverity.HIGH,
                        target_kind=question.target_kind,
                        target_id=question.target_id,
                        next_operation=(
                            f"p2p project readiness questions answer {question.question_id}"
                        ),
                        rationale=f"Question `{question.question_id}` requires owner input.",
                        question_id=question.question_id,
                        question_revision=question.revision,
                    )
                )
        if section.required and applicable and section.open_blocker_ids:
            for blocker_id in section.open_blocker_ids:
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.OWNER_DECISION_BLOCKER,
                        severity=ProjectReadinessGapSeverity.BLOCKER,
                        target_kind="blocker",
                        target_id=blocker_id,
                        next_operation="p2p project readiness questions next",
                        rationale=f"Required section `{section.section_id}` has an unresolved blocker.",
                    )
                )
        has_active_question = any(
            item.applicability == "applicable" and item.state in {"to_answer", "answered"}
            for item in section.question_states
        )
        if section.criteria:
            for criterion in section.criteria:
                if not criterion.applicable or criterion.satisfied:
                    continue
                if criterion.evaluation != "definition_status":
                    continue
                gaps.append(
                    self._gap(
                        snapshot,
                        section=section,
                        kind=ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION,
                        severity=(
                            ProjectReadinessGapSeverity.HIGH
                            if criterion.required
                            else ProjectReadinessGapSeverity.MEDIUM
                        ),
                        target_kind="criterion",
                        target_id=criterion.criterion_id,
                        missing_fields=section.missing_required_fields,
                        next_operation="p2p project readiness questions next",
                        rationale=(
                            f"Active criterion `{criterion.criterion_id}` is not satisfied "
                            f"for section `{section.section_id}`."
                        ),
                    )
                )
        elif (
            not _uses_readiness_v2(snapshot)
            and section.required
            and applicable
            and section.definition_status != "complete"
            and not has_active_question
        ):
            gaps.append(
                self._gap(
                    snapshot,
                    section=section,
                    kind=ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION,
                    severity=ProjectReadinessGapSeverity.HIGH,
                    target_kind="section",
                    target_id=section.section_id,
                    missing_fields=section.missing_required_fields,
                    next_operation="p2p project readiness questions next",
                    rationale=f"Required section `{section.section_id}` is not complete.",
                )
            )
        for assumption in section.assumptions:
            if assumption.status != "to_validate" or not applicable:
                continue
            gaps.append(
                self._gap(
                    snapshot,
                    section=section,
                    kind=ProjectReadinessGapKind.ASSUMPTION_TO_VALIDATE,
                    severity=ProjectReadinessGapSeverity.MEDIUM,
                    target_kind="assumption",
                    target_id=assumption.assumption_id,
                    next_operation="p2p project readiness questions next",
                    rationale=f"Assumption `{assumption.assumption_id}` requires owner validation.",
                    dependency_rank=assumption.dependency_rank,
                )
            )
        if applicable and section.applicable_weight > 0 and section.evidence_weight == 0:
            gaps.append(
                self._gap(
                    snapshot,
                    section=section,
                    kind=ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE,
                    severity=ProjectReadinessGapSeverity.LOW,
                    target_kind="section_evidence",
                    target_id=section.section_id,
                    next_operation="p2p project memory classification --format json",
                    rationale=f"Section `{section.section_id}` has no active section-classified memory evidence.",
                )
            )
        elif (
            not _uses_readiness_v2(snapshot)
            and applicable
            and not section.criteria
            and not section.active_declared_proposals
        ):
            gaps.append(
                self._gap(
                    snapshot,
                    section=section,
                    kind=ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE,
                    severity=ProjectReadinessGapSeverity.LOW,
                    target_kind="section_evidence",
                    target_id=section.section_id,
                    next_operation="p2p project memory classification --format json",
                    rationale=f"Section `{section.section_id}` has no active section-classified memory evidence.",
                )
            )
        return gaps

    def _gap(
        self,
        snapshot: ProjectReadinessSnapshot,
        *,
        section: ProjectReadinessSectionSnapshot | None,
        kind: ProjectReadinessGapKind,
        severity: ProjectReadinessGapSeverity,
        target_kind: str,
        target_id: str,
        next_operation: str,
        rationale: str,
        definition_status: str | None = None,
        missing_fields: Sequence[str] = (),
        heuristic_suggestions: Sequence[str] | None = None,
        dependency_rank: int = 100,
        question_id: str = "",
        question_revision: int | None = None,
    ) -> ProjectReadinessGap:
        section_id = section.section_id if section else ""
        gap_id, digest = readiness_gap_identity(
            vertical_id=snapshot.identity.vertical_id,
            section_id=section_id,
            kind=kind,
            target_kind=target_kind,
            target_id=target_id,
        )
        priority_class = readiness_class_rank(kind)
        section_priority = section.priority if section else 0
        dependency_tie_break = dependency_rank if kind == ProjectReadinessGapKind.ASSUMPTION_TO_VALIDATE else 0
        tie_break: tuple[object, ...] = (priority_class, dependency_tie_break, section_priority, gap_id)
        return ProjectReadinessGap(
            gap_id=gap_id,
            identity_sha256=digest,
            snapshot_fingerprint=snapshot.identity.fingerprint,
            vertical_id=snapshot.identity.vertical_id,
            vertical_version=snapshot.identity.vertical_version,
            vertical_lock_checksum=snapshot.identity.vertical_lock_checksum,
            section_id=section_id,
            target_kind=target_kind,
            target_id=target_id,
            kind=kind,
            severity=severity,
            applicability="applicable",
            definition_status=definition_status or (section.definition_status if section else "not_initialized"),
            missing_fields=tuple(sorted(str(item) for item in missing_fields)),
            declared_evidence=section.active_declared_proposals if section else (),
            heuristic_suggestions=(
                tuple(sorted(str(item) for item in heuristic_suggestions))
                if heuristic_suggestions is not None
                else (section.heuristic_proposals if section else ())
            ),
            required_authority="owner" if kind not in {ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE, ProjectReadinessGapKind.UNMAPPED_PROPOSAL_COVERAGE} else "reviewer",
            owner_input_required=kind not in {ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE, ProjectReadinessGapKind.UNMAPPED_PROPOSAL_COVERAGE},
            question_id=question_id,
            question_revision=question_revision,
            next_operation=next_operation,
            rationale=rationale,
            priority_class=priority_class,
            priority_policy_version=PROJECT_READINESS_GAP_POLICY_VERSION,
            priority_rationale=self._priority_rationale(kind),
            tie_break=tie_break,
            dependency_rank=dependency_rank,
        )

    @staticmethod
    def sort_key(gap: ProjectReadinessGap) -> tuple[object, ...]:
        return gap.tie_break

    @staticmethod
    def _validate_gap_id_collisions(gaps: Sequence[ProjectReadinessGap]) -> None:
        digests: dict[str, str] = {}
        for gap in gaps:
            existing = digests.setdefault(gap.gap_id, gap.identity_sha256)
            if existing != gap.identity_sha256:
                raise ValueError(
                    f"Project readiness gap id collision for `{gap.gap_id}`; full identities differ."
                )

    @staticmethod
    def _priority_rationale(kind: ProjectReadinessGapKind) -> str:
        labels = {
            1: "Integrity, compatibility, authority and owner-decision blockers come first.",
            2: "Owner answers already received should be applied before requesting more input.",
            3: "Incomplete required definition sections precede assumptions and optional evidence.",
            4: "Assumptions are ordered by declared dependency impact with a neutral fallback.",
            5: "Optional declared evidence follows required definition work.",
            6: "Unmapped proposal coverage is informational and lowest priority.",
        }
        return labels[readiness_class_rank(kind)]


class ProjectReadinessPaginationService:
    def page_items(
        self,
        *,
        collection: str,
        snapshot_fingerprint: str,
        items: Sequence[object],
        key: Callable[[object], tuple[object, ...]],
        limit: int = PROJECT_READINESS_DEFAULT_PAGE_SIZE,
        cursor: str = "",
    ) -> ProjectReadinessPage:
        return self._page(
            collection=collection,
            snapshot_fingerprint=snapshot_fingerprint,
            items=items,
            key=key,
            limit=limit,
            cursor=cursor,
        )

    def page_gaps(
        self,
        result: ProjectReadinessResult,
        *,
        limit: int = PROJECT_READINESS_DEFAULT_PAGE_SIZE,
        cursor: str = "",
        predicate: Callable[[ProjectReadinessGap], bool] | None = None,
    ) -> ProjectReadinessPage:
        items = [item for item in result.gaps if predicate is None or predicate(item)]
        return self._page(
            collection="gaps",
            snapshot_fingerprint=result.snapshot.fingerprint,
            items=items,
            key=lambda item: item.tie_break,
            limit=limit,
            cursor=cursor,
        )

    def page_values(
        self,
        *,
        collection: str,
        snapshot_fingerprint: str,
        values: Iterable[str],
        limit: int = PROJECT_READINESS_DEFAULT_PAGE_SIZE,
        cursor: str = "",
    ) -> ProjectReadinessPage:
        items = sorted(dict.fromkeys(str(item) for item in values))
        return self._page(
            collection=collection,
            snapshot_fingerprint=snapshot_fingerprint,
            items=items,
            key=lambda item: (item,),
            limit=limit,
            cursor=cursor,
        )

    def _page(
        self,
        *,
        collection: str,
        snapshot_fingerprint: str,
        items: Sequence[object],
        key: Callable[[object], tuple[object, ...]],
        limit: int,
        cursor: str,
    ) -> ProjectReadinessPage:
        normalized_limit = int(limit)
        if normalized_limit < 1 or normalized_limit > PROJECT_READINESS_MAX_PAGE_SIZE:
            raise ValueError(f"Readiness page limit must be between 1 and {PROJECT_READINESS_MAX_PAGE_SIZE}.")
        start = 0
        if cursor:
            decoded = ProjectReadinessCursor.decode(cursor)
            if decoded.collection != collection:
                raise ValueError("Readiness cursor belongs to a different collection.")
            if decoded.policy_version != PROJECT_READINESS_CURSOR_POLICY_VERSION:
                raise ValueError("Readiness cursor policy changed. Restart pagination without a cursor.")
            if decoded.snapshot_fingerprint != snapshot_fingerprint:
                raise ValueError(
                    "P2P349_PROJECT_READINESS_CURSOR_STALE: stale_cursor: readiness sources changed; "
                    "restart pagination without a cursor."
                )
            for index, item in enumerate(items):
                if tuple(key(item)) == decoded.last_key:
                    start = index + 1
                    break
            else:
                raise ValueError(
                    "P2P349_PROJECT_READINESS_CURSOR_STALE: stale_cursor: cursor key is no longer present; "
                    "restart pagination."
                )
        selected = tuple(items[start : start + normalized_limit])
        diagnostics: tuple[ProjectReadinessDiagnostic, ...] = ()
        payload_bytes = self._payload_size(selected)
        while selected and payload_bytes > PROJECT_READINESS_DEFAULT_PAYLOAD_BYTES:
            selected = selected[:-1]
            payload_bytes = self._payload_size(selected)
        if not selected and start < len(items):
            diagnostics = (
                ProjectReadinessDiagnostic(
                    code="P2P353_READINESS_PAYLOAD_LIMIT",
                    severity="warning",
                    message=(
                        "The next readiness record exceeds the default payload budget. "
                        "Use a narrower collection filter or detail request."
                    ),
                ),
            )
        truncated = start + len(selected) < len(items)
        next_cursor = ""
        if truncated and selected:
            next_cursor = ProjectReadinessCursor(
                collection=collection,
                snapshot_fingerprint=snapshot_fingerprint,
                policy_version=PROJECT_READINESS_CURSOR_POLICY_VERSION,
                last_key=tuple(key(selected[-1])),
            ).encode()
        return ProjectReadinessPage(
            collection=collection,
            snapshot_fingerprint=snapshot_fingerprint,
            items=selected,
            total=len(items),
            limit=normalized_limit,
            next_cursor=next_cursor,
            truncated=truncated,
            payload_bytes=payload_bytes,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _payload_size(items: Sequence[object]) -> int:
        from p2p_engine.core.mutation_preview import canonical_json_bytes

        values = []
        for item in items:
            to_dict = getattr(item, "to_dict", None)
            values.append(to_dict() if callable(to_dict) else item)
        return len(canonical_json_bytes(values))


def attach_question_reference(
    gap: ProjectReadinessGap,
    *,
    question_id: str,
    question_revision: int,
    next_operation: str,
) -> ProjectReadinessGap:
    return replace(
        gap,
        question_id=question_id,
        question_revision=question_revision,
        next_operation=next_operation,
    )
