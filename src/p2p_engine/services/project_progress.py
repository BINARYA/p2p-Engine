from __future__ import annotations

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
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.vertical_service = vertical_service
        self.proposal_summaries = proposal_summaries

    def status(
        self,
        *,
        proposal_summaries_snapshot: list[_ProposalLike] | None = None,
    ) -> ProjectProgress:
        active = self.vertical_service.active_vertical()
        pack = self.vertical_service.show_vertical(active.vertical_id)
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
        declared_committed: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        declared_other: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        heuristic: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        warnings: list[str] = []
        for proposal in proposals:
            status = self.vertical_service.proposal_vertical_coverage_status(proposal.proposal_id)
            if status.state == "valid" and status.coverage is not None:
                target = declared_committed if is_active_project_projection(proposal.status) else declared_other
                for section in status.coverage.sections:
                    target.setdefault(section.section_id, []).append(proposal.proposal_id)
            elif status.state in {"invalid", "vertical_mismatch"}:
                warnings.append(f"{proposal.proposal_id}: vertical coverage is {status.state}.")
            if status.state != "valid":
                suggestion = self.vertical_service.suggest_proposal_vertical_coverage(proposal.proposal_id)
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
                questions.extend(
                    {"section_id": section.section_id, "id": item.question_id, "text": item.question}
                    for item in state.open_questions
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
                exclusions={"optional_sections": excluded_optional, "heuristic_suggestions": sum(len(items) for items in heuristic.values())},
            ),
            basis="owner_declared_vertical_coverage_from_active_committed_proposals",
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
            warnings=tuple(sorted(warnings)),
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
