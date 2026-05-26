from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContributionType(StrEnum):
    feature_request = "feature_request"
    alternative_proposal = "alternative_proposal"
    architectural_principle = "architectural_principle"
    objective = "objective"
    constraint = "constraint"
    risk = "risk"
    suggestion = "suggestion"
    objection = "objection"
    implementation_suggestion = "implementation_suggestion"
    scope_boundary = "scope_boundary"


@dataclass(frozen=True)
class Contribution:
    contribution_id: str
    contribution_type: ContributionType
    text: str
    author: str
    relevance_hint: str

