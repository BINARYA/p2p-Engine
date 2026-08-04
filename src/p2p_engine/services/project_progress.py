from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from p2p_engine.core.project_progress import (
    PROJECT_PROGRESS_POLICY_VERSION,
    ProgressAxis,
    ProgressRatio,
    ProgressSectionEvidence,
    ProjectProgress,
)
from p2p_engine.services.lifecycle_authority import (
    PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION,
    is_active_project_projection,
)
from p2p_engine.services.project_verticals import ProjectVerticalService, _section_fields
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.core.vertical_memory import VerticalProjectMemoryView


class _ProposalLike(Protocol):
    proposal_id: str
    status: str


class ProjectProgressService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: ProjectVerticalService,
        proposal_summaries: Callable[[], list[_ProposalLike]],
        question_service: ProjectQuestionStateService | None = None,
        vertical_memory_view: Callable[[], VerticalProjectMemoryView] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.vertical_service = vertical_service
        self.proposal_summaries = proposal_summaries
        self.question_service = question_service or ProjectQuestionStateService(root=root, p2p_dir=p2p_dir)
        self.vertical_memory_view = vertical_memory_view

    def status(
        self,
        *,
        proposal_summaries_snapshot: list[_ProposalLike] | None = None,
        include_heuristics: bool = False,
        vertical_memory_snapshot: VerticalProjectMemoryView | None = None,
    ) -> ProjectProgress:
        if vertical_memory_snapshot is not None and not include_heuristics:
            return self._status_from_memory(
                vertical_memory_snapshot,
                include_heuristics=False,
            )
        if (
            proposal_summaries_snapshot is None
            and not include_heuristics
            and self.vertical_memory_view is not None
        ):
            return self._status_from_memory(
                self.vertical_memory_view(),
                include_heuristics=include_heuristics,
            )
        vertical_state = self.vertical_service.vertical_read_state()
        active = vertical_state.active
        pack = vertical_state.pack
        definition_view = self.vertical_service.project_definition_view()
        definition_state = definition_view.state if definition_view.exists and definition_view.valid else None
        state_by_section = {
            section.section_id: section for section in definition_state.sections
        } if definition_state else {}
        proposals = (
            proposal_summaries_snapshot
            if proposal_summaries_snapshot is not None
            else self.proposal_summaries()
        )
        proposal_ids = [proposal.proposal_id for proposal in proposals]
        coverage_statuses = self.vertical_service.proposal_vertical_coverage_statuses(
            proposal_ids,
            state=vertical_state,
        )
        suggestions = (
            self.vertical_service.suggest_proposal_vertical_coverages(
                [
                    proposal_id
                    for proposal_id in proposal_ids
                    if coverage_statuses[proposal_id].state != "valid"
                ],
                state=vertical_state,
            )
            if include_heuristics
            else {}
        )
        declared_committed: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        declared_other: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        heuristic: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        warnings: list[str] = []
        for proposal in proposals:
            status = coverage_statuses[proposal.proposal_id]
            if status.state == "valid" and status.coverage is not None:
                target = declared_committed if is_active_project_projection(proposal.status) else declared_other
                for section in status.coverage.sections:
                    target.setdefault(section.section_id, []).append(proposal.proposal_id)
            elif status.state in {"invalid", "vertical_mismatch"}:
                warnings.append(f"{proposal.proposal_id}: vertical coverage is {status.state}.")
            if status.state != "valid" and include_heuristics:
                suggestion = suggestions[proposal.proposal_id]
                for candidate in suggestion.candidates:
                    heuristic.setdefault(candidate.section_id, []).append(proposal.proposal_id)

        section_results: list[ProgressSectionEvidence] = []
        definition_numerator = 0
        definition_denominator = 0
        evidence_numerator = 0
        evidence_denominator = 0
        excluded_optional = 0
        excluded_not_applicable = 0
        blockers: list[dict[str, str]] = []
        questions: list[dict[str, str]] = []
        assumptions: list[dict[str, str]] = []
        for section in sorted(pack.sections, key=lambda item: item.priority):
            state = state_by_section.get(section.section_id)
            definition_status = state.status if state else "not_initialized"
            required_fields = [field for field in _section_fields(section, pack) if field.required]
            complete_fields = sum(
                1 for field in required_fields
                if state is not None and field.field_id in state.fields and state.fields[field.field_id].value not in (None, "", [], {})
            )
            if not section.required:
                excluded_optional += 1
                definition_units_total = 0
                definition_units_complete = 0
            elif state is not None and state.status == "not_applicable":
                excluded_not_applicable += 1
                definition_units_total = 0
                definition_units_complete = 0
            else:
                definition_units_total = len(required_fields) + 1 if required_fields else 1
                definition_units_complete = complete_fields + (1 if state is not None and state.status == "complete" else 0)
                definition_denominator += definition_units_total
                definition_numerator += definition_units_complete
            if section.required and not (state is not None and state.status == "not_applicable"):
                evidence_denominator += 1
                if declared_committed.get(section.section_id):
                    evidence_numerator += 1
            if state is not None:
                blockers.extend(
                    {"section_id": section.section_id, "id": item.blocker_id, "text": item.text}
                    for item in state.blockers
                )
                assumptions.extend(
                    {
                        "section_id": section.section_id,
                        "id": item.assumption_id,
                        "text": item.text,
                        "status": item.status,
                    }
                    for item in state.assumptions
                )
            section_results.append(
                ProgressSectionEvidence(
                    section_id=section.section_id,
                    required=section.required,
                    definition_status=definition_status,
                    required_fields_complete=complete_fields,
                    required_fields_total=len(required_fields),
                    definition_units_complete=definition_units_complete,
                    definition_units_total=definition_units_total,
                    declared_committed_proposals=tuple(sorted(declared_committed.get(section.section_id, []))),
                    declared_non_committed_proposals=tuple(sorted(declared_other.get(section.section_id, []))),
                    heuristic_proposals=tuple(sorted(heuristic.get(section.section_id, []))),
                )
            )

        definition_axis = ProgressAxis(
            axis_id="definition_completeness",
            status=("not_initialized" if definition_state is None else "measured"),
            ratio=self._ratio(
                definition_numerator if definition_state is not None else 0,
                definition_denominator if definition_state is not None else 0,
                exclusions={"optional_sections": excluded_optional, "not_applicable_sections": excluded_not_applicable},
                percentage_allowed=definition_state is not None,
            ),
            basis="explicit_section_status_and_required_fields",
        )
        evidence_axis = ProgressAxis(
            axis_id="declared_evidence_coverage",
            status="measured",
            ratio=self._ratio(
                evidence_numerator,
                evidence_denominator,
                exclusions={
                    "optional_sections": excluded_optional,
                    "heuristic_suggestions": sum(len(items) for items in heuristic.values()),
                    "heuristics_not_requested": 0 if include_heuristics else 1,
                },
            ),
            basis="owner_declared_vertical_coverage_from_active_committed_proposals",
        )
        question_counts: Counter[str] = Counter()
        question_artifact = self.question_service.read_optional()
        active_question_sections: set[str] = set()
        if question_artifact is not None:
            question_counts.update(item.state.value for item in question_artifact.questions)
            for item in question_artifact.questions:
                if item.applicability.value == "active":
                    active_question_sections.add(item.section_id)
                else:
                    question_counts[item.applicability.value] += 1
        question_counts["no_safe_question"] = (
            sum(
                1
                for section in pack.sections
                if section.required
                and section.section_id not in active_question_sections
                and (
                    state_by_section.get(section.section_id) is None
                    or state_by_section[section.section_id].status not in {"complete", "not_applicable"}
                )
            )
            if question_artifact is not None
            else 0
        )
        return ProjectProgress(
            vertical_id=active.vertical_id,
            policy_version=PROJECT_PROGRESS_POLICY_VERSION,
            lifecycle_authority_policy_version=PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION,
            definition=definition_axis,
            evidence=evidence_axis,
            sections=tuple(section_results),
            blockers=tuple(blockers),
            open_questions=tuple(questions),
            assumptions=tuple(assumptions),
            question_counts=dict(sorted(question_counts.items())),
            warnings=tuple(sorted(warnings)),
        )

    def _status_from_memory(
        self,
        view: VerticalProjectMemoryView,
        *,
        include_heuristics: bool,
    ) -> ProjectProgress:
        section_results: list[ProgressSectionEvidence] = []
        definition_numerator = 0
        definition_denominator = 0
        evidence_numerator = 0
        evidence_denominator = 0
        excluded_optional = 0
        excluded_not_applicable = 0
        blockers: list[dict[str, str]] = []
        questions: list[dict[str, str]] = []
        assumptions: list[dict[str, str]] = []
        question_counts: Counter[str] = Counter()
        active_question_sections: set[str] = set()
        heuristic_by_section: dict[str, list[str]] = {}
        if include_heuristics:
            for proposal in view.unmapped_active_proposals:
                proposal_id = str(proposal.get("proposal_id") or "")
                for section_id in proposal.get("heuristic_sections", ()):
                    heuristic_by_section.setdefault(str(section_id), []).append(proposal_id)

        definition_exists = view.definition_exists and view.definition_valid
        for section in view.sections:
            definition = section.definition
            definition_status = str(definition.get("status") or "not_initialized")
            required_ids = tuple(
                str(item) for item in definition.get("required_field_ids", ())
            )
            fields = definition.get("fields")
            fields = fields if isinstance(fields, dict) else {}
            complete_fields = sum(
                1
                for field_id in required_ids
                if isinstance(fields.get(field_id), dict)
                and fields[field_id].get("value") not in (None, "", [], {})
            )
            if not section.required:
                excluded_optional += 1
                definition_units_total = 0
                definition_units_complete = 0
            elif definition_status == "not_applicable":
                excluded_not_applicable += 1
                definition_units_total = 0
                definition_units_complete = 0
            else:
                definition_units_total = len(required_ids) + 1 if required_ids else 1
                definition_units_complete = complete_fields + (1 if definition_status == "complete" else 0)
                definition_denominator += definition_units_total
                definition_numerator += definition_units_complete
            active_ids = tuple(
                sorted({item.proposal_id for item in section.active_contributions})
            )
            historical_ids = tuple(
                sorted({item.proposal_id for item in section.historical_contributions})
            )
            if section.required and definition_status != "not_applicable":
                evidence_denominator += 1
                if active_ids:
                    evidence_numerator += 1
            blockers.extend(
                {
                    "section_id": section.section_id,
                    "id": str(item.get("id") or ""),
                    "text": str(item.get("text") or ""),
                }
                for item in definition.get("blockers", ())
                if isinstance(item, dict)
            )
            blockers.extend(
                {
                    "section_id": section.section_id,
                    "id": str(item.get("id") or ""),
                    "text": str(item.get("reason") or "Unresolved project conflict."),
                }
                for item in section.conflicts
                if str(item.get("kind") or "") == "conflict"
                and str(item.get("status") or "") == "unresolved"
            )
            assumptions.extend(
                {
                    "section_id": section.section_id,
                    "id": str(item.get("id") or ""),
                    "text": str(item.get("text") or ""),
                    "status": str(item.get("status") or ""),
                }
                for item in definition.get("assumptions", ())
                if isinstance(item, dict)
            )
            for item in section.questions:
                question_counts[str(item.get("state") or "unknown")] += 1
                applicability = str(item.get("applicability") or "active")
                if applicability == "active":
                    active_question_sections.add(section.section_id)
                else:
                    question_counts[applicability] += 1
            section_results.append(
                ProgressSectionEvidence(
                    section_id=section.section_id,
                    required=section.required,
                    definition_status=definition_status,
                    required_fields_complete=complete_fields,
                    required_fields_total=len(required_ids),
                    definition_units_complete=definition_units_complete,
                    definition_units_total=definition_units_total,
                    declared_committed_proposals=active_ids,
                    declared_non_committed_proposals=historical_ids,
                    heuristic_proposals=tuple(
                        sorted(set(heuristic_by_section.get(section.section_id, ())))
                    ),
                )
            )

        question_counts["no_safe_question"] = sum(
            1
            for section in view.sections
            if section.required
            and section.section_id not in active_question_sections
            and str(section.definition.get("status") or "not_initialized")
            not in {"complete", "not_applicable"}
        )
        definition_axis = ProgressAxis(
            axis_id="definition_completeness",
            status="measured" if definition_exists else "not_initialized",
            ratio=self._ratio(
                definition_numerator if definition_exists else 0,
                definition_denominator if definition_exists else 0,
                exclusions={
                    "optional_sections": excluded_optional,
                    "not_applicable_sections": excluded_not_applicable,
                },
                percentage_allowed=definition_exists,
            ),
            basis="explicit_section_status_and_required_fields",
        )
        evidence_axis = ProgressAxis(
            axis_id="declared_evidence_coverage",
            status="measured",
            ratio=self._ratio(
                evidence_numerator,
                evidence_denominator,
                exclusions={
                    "optional_sections": excluded_optional,
                    "heuristic_suggestions": sum(len(items) for items in heuristic_by_section.values()),
                    "heuristics_not_requested": 0 if include_heuristics else 1,
                },
            ),
            basis="owner_declared_vertical_coverage_from_active_committed_proposals",
        )
        warnings = tuple(
            sorted(
                str(item.get("message") or item.get("code") or "")
                for item in view.diagnostics
                if str(item.get("code") or "").startswith("VERTICAL_MEMORY_INVALID_COVERAGE")
            )
        )
        return ProjectProgress(
            vertical_id=view.vertical_id,
            policy_version=PROJECT_PROGRESS_POLICY_VERSION,
            lifecycle_authority_policy_version=PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION,
            definition=definition_axis,
            evidence=evidence_axis,
            sections=tuple(section_results),
            blockers=tuple(blockers),
            open_questions=tuple(questions),
            assumptions=tuple(assumptions),
            question_counts=dict(sorted(question_counts.items())),
            warnings=warnings,
        )

    @staticmethod
    def _ratio(
        numerator: int,
        denominator: int,
        *,
        exclusions: dict[str, int],
        percentage_allowed: bool = True,
    ) -> ProgressRatio:
        percentage = round(numerator * 100 / denominator, 2) if percentage_allowed and denominator else None
        return ProgressRatio(
            numerator=numerator,
            denominator=denominator,
            percentage=percentage,
            exclusions=exclusions,
        )
