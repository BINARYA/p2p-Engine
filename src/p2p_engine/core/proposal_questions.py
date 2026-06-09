from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ProposalQuestionPriority(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class ProposalQuestionState(StrEnum):
    to_answer = "to_answer"
    defer = "defer"
    muted = "muted"
    answered = "answered"
    applied = "applied"
    retired = "retired"
    superseded = "superseded"


@dataclass(frozen=True)
class ProposalQuestionApplyPlanItem:
    artifact: str
    action: str
    status: str
    reason: str


@dataclass(frozen=True)
class ProposalQuestionGroup:
    group_id: str
    gap: str
    state: ProposalQuestionState
    priority: ProposalQuestionPriority
    rationale: str


@dataclass(frozen=True)
class ProposalQuestion:
    question_id: str
    group_id: str
    gap: str
    criterion: str
    priority: ProposalQuestionPriority
    state: ProposalQuestionState
    question: str
    rationale: str
    answer: str
    answer_source: str
    answered_at: str
    asked_count: int
    last_asked_at: str
    derived_from: list[str]
    superseded_by: str
    muted_reason: str
    deferred_reason: str
    applied_to_proposal: bool
    applied_at: str
    apply_plan: list[ProposalQuestionApplyPlanItem]
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str


@dataclass(frozen=True)
class ProposalQuestionStateView:
    proposal_id: str
    status: str
    path: Path
    schema_version: int | None
    groups: list[ProposalQuestionGroup]
    questions: list[ProposalQuestion]


@dataclass(frozen=True)
class ProposalQuestionOperation:
    proposal_id: str
    path: Path
    question: ProposalQuestion | None
    message: str


@dataclass(frozen=True)
class ProposalQuestionApplySummary:
    proposal_id: str
    path: Path
    applied_questions: list[ProposalQuestion]
    update_plan: list[ProposalQuestionApplyPlanItem]
    summary: str
