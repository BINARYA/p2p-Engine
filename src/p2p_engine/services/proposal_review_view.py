from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from p2p_engine.core.contribution import Contribution, ContributionType
from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactExpectation,
    ProposalArtifactRecord,
    ProposalArtifactStateView,
    ProposalArtifactStatus,
)
from p2p_engine.core.proposal_questions import ProposalQuestion, ProposalQuestionStateView
from p2p_engine.foundation.markdown import read_markdown_section
from p2p_engine.services.proposals import ProposalContributionList, ProposalDetail
from p2p_engine.services.readiness import ProposalReadiness


MATERIALIZATION_CANONICAL = "canonical_state"
MATERIALIZATION_GENERATED = "generated_file"
MATERIALIZATION_IMPORTED = "imported_file"
MATERIALIZATION_LEGACY = "legacy_file"
MATERIALIZATION_NOT_MATERIALIZED = "not_materialized"
MATERIALIZATION_UNKNOWN = "unknown"

PROVENANCE_EXPLICIT = "explicit"
PROVENANCE_INFERRED = "inferred"
PROVENANCE_UNKNOWN = "unknown"

SUMMARY_LIMIT = 240


@dataclass(frozen=True)
class ProposalArtifactCatalogItem:
    key: str
    label: str
    filename: str
    expectation: ProposalArtifactExpectation
    status: ProposalArtifactStatus
    materialization_kind: str
    source_hint: str
    provenance_confidence: str
    path: Path | None
    summary: str
    next_action: str


@dataclass(frozen=True)
class ProposalQuestionGroupsView:
    proposal_id: str
    status: str
    path: Path
    owner_questions: list[ProposalQuestion]
    analytical_open_questions: list[Contribution]
    legacy_question_artifacts: list[ProposalArtifactCatalogItem]


@dataclass(frozen=True)
class ProposalFullView:
    proposal_id: str
    title: str
    status: str
    path: Path
    core_sections: dict[str, str]
    decision: dict[str, str]
    readiness: ProposalReadiness
    contributions: ProposalContributionList
    artifact_status: list[ProposalArtifactCatalogItem]
    questions: ProposalQuestionGroupsView
    narrative_artifacts: list[ProposalArtifactCatalogItem]
    next_actions: list[str]


@dataclass(frozen=True)
class _ArtifactSlot:
    key: str
    label: str
    filename: str
    expectation: ProposalArtifactExpectation
    materialization_kind: str
    narrative: bool = False
    empty_file_satisfied: bool = False


ARTIFACT_SLOTS: tuple[_ArtifactSlot, ...] = (
    _ArtifactSlot("proposal", "Proposal Body", "proposal.md", ProposalArtifactExpectation.required, MATERIALIZATION_CANONICAL),
    _ArtifactSlot("decision", "Decision State", "decision.md", ProposalArtifactExpectation.required, MATERIALIZATION_CANONICAL, empty_file_satisfied=True),
    _ArtifactSlot("readiness", "Readiness Snapshot", "readiness.yml", ProposalArtifactExpectation.required, MATERIALIZATION_CANONICAL),
    _ArtifactSlot("contributions", "Structured Contributions", "contributions.yml", ProposalArtifactExpectation.optional_memory, MATERIALIZATION_CANONICAL, empty_file_satisfied=True),
    _ArtifactSlot("questions", "Structured Owner Questions", "questions.yml", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_CANONICAL, empty_file_satisfied=True),
    _ArtifactSlot("open_questions", "Legacy Open Questions", "open-questions.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED, narrative=True),
    _ArtifactSlot("clarifications", "Clarifications", "clarifications.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_GENERATED, narrative=True),
    _ArtifactSlot("findings", "Findings", "findings.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED, narrative=True),
    _ArtifactSlot("exploration", "Exploration", "exploration.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED, narrative=True),
    _ArtifactSlot("alternatives", "Alternatives", "alternatives.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED, narrative=True),
    _ArtifactSlot("risks", "Risks", "risks.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED, narrative=True),
    _ArtifactSlot("assumptions", "Assumptions", "assumptions.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED, narrative=True),
    _ArtifactSlot("suggested_scope", "Suggested Scope", "suggested-scope.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED, narrative=True),
    _ArtifactSlot("impact_map", "Impact Map", "impact-map.yml", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED),
    _ArtifactSlot("related_proposals", "Related Proposals", "related-proposals.yml", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED),
    _ArtifactSlot("conflict_analysis", "Conflict Analysis", "conflict-analysis.yml", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED),
    _ArtifactSlot("vertical_coverage", "Vertical Coverage", "vertical-coverage.yml", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_IMPORTED),
    _ArtifactSlot("ai_digest", "AI Digest", "ai-digest.md", ProposalArtifactExpectation.optional_memory, MATERIALIZATION_GENERATED, narrative=True),
    _ArtifactSlot("execution_plan", "Execution Plan", "execution-plan.md", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_GENERATED, narrative=True),
    _ArtifactSlot("tasks", "Implementation Tasks", "tasks.yml", ProposalArtifactExpectation.required_when_applicable, MATERIALIZATION_GENERATED, empty_file_satisfied=True),
)


class ProposalReviewViewService:
    def __init__(
        self,
        *,
        root: Path,
        find_proposal_dir: Callable[[str], Path],
        show_proposal: Callable[[str], ProposalDetail],
        read_proposal_readiness: Callable[[str], ProposalReadiness],
        read_proposal_questions: Callable[[str], ProposalQuestionStateView],
        read_proposal_artifacts: Callable[[str], ProposalArtifactStateView],
        list_contributions: Callable[[str], ProposalContributionList],
    ) -> None:
        self.root = root
        self.find_proposal_dir = find_proposal_dir
        self.show_proposal = show_proposal
        self.read_proposal_readiness = read_proposal_readiness
        self.read_proposal_questions = read_proposal_questions
        self.read_proposal_artifacts = read_proposal_artifacts
        self.list_contributions = list_contributions

    def artifact_catalog(self, proposal_id: str) -> list[ProposalArtifactCatalogItem]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        artifact_state = self.read_proposal_artifacts(proposal_id)
        records = {record.artifact_id: record for record in artifact_state.artifacts}
        return [
            self._catalog_item(proposal_id, proposal_dir, artifact_state, slot, records.get(slot.key))
            for slot in ARTIFACT_SLOTS
        ]

    def full_view(self, proposal_id: str) -> ProposalFullView:
        proposal = self.show_proposal(proposal_id)
        proposal_dir = self.find_proposal_dir(proposal_id)
        artifact_status = self.artifact_catalog(proposal_id)
        readiness = self.read_proposal_readiness(proposal_id)
        contributions = self.list_contributions(proposal_id)
        questions = self._question_groups(proposal_id, artifact_status, contributions)
        narrative_artifacts = [
            item
            for item in artifact_status
            if item.path is not None and _slot_for(item.key).narrative
        ]
        return ProposalFullView(
            proposal_id=proposal.proposal_id,
            title=proposal.title,
            status=proposal.status,
            path=proposal.path,
            core_sections=self._core_sections(proposal_dir),
            decision={
                "status": proposal.decision_status,
                "reason": proposal.decision_reason,
            },
            readiness=readiness,
            contributions=contributions,
            artifact_status=artifact_status,
            questions=questions,
            narrative_artifacts=narrative_artifacts,
            next_actions=_unique_actions(
                [
                    *readiness.suggested_next,
                    *[item.next_action for item in artifact_status],
                    *self._question_next_actions(proposal_id, questions),
                ]
            ),
        )

    def _catalog_item(
        self,
        proposal_id: str,
        proposal_dir: Path,
        artifact_state: ProposalArtifactStateView,
        slot: _ArtifactSlot,
        record: ProposalArtifactRecord | None,
    ) -> ProposalArtifactCatalogItem:
        path = proposal_dir / slot.filename
        path_exists = path.exists()
        relative_path = _relative_to_root(path, self.root) if path_exists else None
        expectation = record.expectation if record is not None else slot.expectation
        inferred_status = _inferred_status(path, expectation, slot)
        status = _combined_status(record, inferred_status, path_exists=path_exists)
        materialization_kind = _materialization_kind(slot, path_exists=path_exists, artifact_state=artifact_state)
        source_hint = slot.filename if path_exists else "none"
        provenance_confidence = _provenance_confidence(record, path_exists=path_exists)
        summary = _summary_for_path(path)
        return ProposalArtifactCatalogItem(
            key=slot.key,
            label=slot.label,
            filename=slot.filename,
            expectation=expectation,
            status=status,
            materialization_kind=materialization_kind,
            source_hint=source_hint,
            provenance_confidence=provenance_confidence,
            path=relative_path,
            summary=summary,
            next_action=_next_action(proposal_id, slot, expectation, status),
        )

    def _core_sections(self, proposal_dir: Path) -> dict[str, str]:
        proposal_path = proposal_dir / "proposal.md"
        text = proposal_path.read_text(encoding="utf-8") if proposal_path.exists() else ""
        sections = {
            "problem": "Problem",
            "context": "Context",
            "goals": "Goals",
            "non_goals": "Non-Goals",
            "proposal": "Proposal",
            "acceptance_criteria": "Acceptance Criteria",
        }
        return {
            key: read_markdown_section(text, title) or ""
            for key, title in sections.items()
        }

    def _question_groups(
        self,
        proposal_id: str,
        artifact_status: list[ProposalArtifactCatalogItem],
        contributions: ProposalContributionList,
    ) -> ProposalQuestionGroupsView:
        question_state = self.read_proposal_questions(proposal_id)
        analytical_open_questions = [
            item
            for item in contributions.contributions
            if item.contribution_type == ContributionType.open_question
        ]
        legacy_question_artifacts = [
            item
            for item in artifact_status
            if item.key == "open_questions" and item.path is not None
        ]
        return ProposalQuestionGroupsView(
            proposal_id=proposal_id,
            status=question_state.status,
            path=question_state.path,
            owner_questions=question_state.questions,
            analytical_open_questions=analytical_open_questions,
            legacy_question_artifacts=legacy_question_artifacts,
        )

    def _question_next_actions(self, proposal_id: str, questions: ProposalQuestionGroupsView) -> list[str]:
        if questions.status == "not_initialized":
            return [f"p2p proposal questions init {proposal_id}"]
        if any(question.state.value == "to_answer" for question in questions.owner_questions):
            return [f"p2p proposal questions next {proposal_id}"]
        return []


def _slot_for(key: str) -> _ArtifactSlot:
    for slot in ARTIFACT_SLOTS:
        if slot.key == key:
            return slot
    raise ValueError(f"Unknown artifact slot: {key}")


def _relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _inferred_status(
    path: Path,
    expectation: ProposalArtifactExpectation,
    slot: _ArtifactSlot,
) -> ProposalArtifactStatus:
    if not path.exists():
        if expectation == ProposalArtifactExpectation.optional_memory:
            return ProposalArtifactStatus.unknown
        if expectation == ProposalArtifactExpectation.not_expected:
            return ProposalArtifactStatus.not_applicable
        return ProposalArtifactStatus.missing
    if slot.empty_file_satisfied:
        return ProposalArtifactStatus.satisfied
    quality = _artifact_quality(path.read_text(encoding="utf-8"))
    if quality == "missing":
        return ProposalArtifactStatus.missing
    if quality == "weak":
        return ProposalArtifactStatus.weak
    return ProposalArtifactStatus.satisfied


def _combined_status(
    record: ProposalArtifactRecord | None,
    inferred_status: ProposalArtifactStatus,
    *,
    path_exists: bool,
) -> ProposalArtifactStatus:
    if record is None:
        return inferred_status
    if record.status in {ProposalArtifactStatus.deferred, ProposalArtifactStatus.not_applicable}:
        return record.status
    if not path_exists:
        return inferred_status
    if record.status in {
        ProposalArtifactStatus.unknown,
        ProposalArtifactStatus.missing,
        ProposalArtifactStatus.weak,
        ProposalArtifactStatus.absent_legacy,
    }:
        return inferred_status
    return record.status


def _artifact_quality(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "missing"
    lowered = stripped.lower()
    placeholders = (
        "pending.",
        "not explored yet.",
        "none identified yet.",
        "none recorded yet.",
        "not generated yet.",
        "findings: []",
    )
    if any(placeholder in lowered for placeholder in placeholders):
        return "weak"
    content = " ".join(
        line.strip()
        for line in stripped.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if len(content) < 40:
        return "weak"
    return "satisfied"


def _materialization_kind(
    slot: _ArtifactSlot,
    *,
    path_exists: bool,
    artifact_state: ProposalArtifactStateView,
) -> str:
    if not path_exists:
        return MATERIALIZATION_NOT_MATERIALIZED
    if artifact_state.legacy_state == ProposalArtifactStatus.absent_legacy and slot.materialization_kind == MATERIALIZATION_IMPORTED:
        return MATERIALIZATION_LEGACY
    return slot.materialization_kind or MATERIALIZATION_UNKNOWN


def _provenance_confidence(
    record: ProposalArtifactRecord | None,
    *,
    path_exists: bool,
) -> str:
    if record is not None:
        return PROVENANCE_EXPLICIT
    if path_exists:
        return PROVENANCE_INFERRED
    return PROVENANCE_UNKNOWN


def _summary_for_path(path: Path) -> str:
    if not path.exists():
        return ""
    return _clip_summary(_summary_text(path.read_text(encoding="utf-8")))


def _summary_text(text: str) -> str:
    lines: list[str] = []
    in_frontmatter = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if stripped.startswith("#"):
            continue
        lines.append(stripped)
    return " ".join(lines)


def _clip_summary(text: str) -> str:
    stripped = " ".join(text.split())
    if len(stripped) <= SUMMARY_LIMIT:
        return stripped
    return stripped[: SUMMARY_LIMIT - 3].rstrip() + "..."


def _next_action(
    proposal_id: str,
    slot: _ArtifactSlot,
    expectation: ProposalArtifactExpectation,
    status: ProposalArtifactStatus,
) -> str:
    if status not in {ProposalArtifactStatus.missing, ProposalArtifactStatus.weak, ProposalArtifactStatus.unknown}:
        return ""
    if expectation == ProposalArtifactExpectation.optional_memory and status == ProposalArtifactStatus.unknown:
        return ""
    commands = {
        "proposal": f"p2p proposal update {proposal_id}",
        "readiness": f"p2p proposal readiness init {proposal_id}",
        "questions": f"p2p proposal questions init {proposal_id}",
        "open_questions": f"p2p proposal questions init {proposal_id}",
        "clarifications": f"p2p clarify prompt {proposal_id}",
        "findings": f"p2p explore prompt {proposal_id}",
        "exploration": f"p2p explore prompt {proposal_id}",
        "alternatives": f"p2p explore prompt {proposal_id}",
        "risks": f"p2p explore prompt {proposal_id}",
        "assumptions": f"p2p explore prompt {proposal_id}",
        "suggested_scope": f"p2p explore prompt {proposal_id}",
        "impact_map": f"p2p impact prompt {proposal_id}",
        "related_proposals": f"p2p impact prompt {proposal_id}",
        "conflict_analysis": f"p2p impact prompt {proposal_id}",
        "execution_plan": f"p2p plan prompt {proposal_id}",
        "tasks": f"p2p tasks prompt {proposal_id}",
    }
    return commands.get(slot.key, "")


def _unique_actions(actions: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for action in actions:
        stripped = action.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        unique.append(stripped)
    return unique
