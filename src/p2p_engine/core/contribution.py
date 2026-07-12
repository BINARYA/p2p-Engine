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
    finding = "finding"
    open_question = "open_question"
    alternative = "alternative"
    assumption = "assumption"


@dataclass(frozen=True)
class Contribution:
    contribution_id: str
    contribution_type: ContributionType
    text: str
    author: str
    relevance_hint: str


def allowed_contribution_type_values() -> tuple[str, ...]:
    return tuple(item.value for item in ContributionType)


def allowed_contribution_type_text() -> str:
    return ", ".join(allowed_contribution_type_values())


def parse_contribution_type(value: object) -> ContributionType:
    raw_value = str(value or ContributionType.suggestion.value)
    try:
        return ContributionType(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid contribution type: {raw_value}. Allowed: {allowed_contribution_type_text()}"
        ) from exc
