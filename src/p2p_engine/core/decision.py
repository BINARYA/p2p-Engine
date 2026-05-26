from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class DecisionOutcome(StrEnum):
    accepted = "accepted"
    accepted_with_changes = "accepted_with_changes"
    rejected = "rejected"
    deferred = "deferred"
    split = "split"
    merged_into_other = "merged_into_other"
    superseded = "superseded"


@dataclass(frozen=True)
class Decision:
    proposal_id: str
    outcome: DecisionOutcome
    reason: str
    approver: str
    decided_on: date

