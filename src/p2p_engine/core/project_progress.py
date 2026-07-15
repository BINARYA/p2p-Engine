from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


PROJECT_PROGRESS_POLICY_VERSION = 1


@dataclass(frozen=True)
class ProgressRatio:
    numerator: int
    denominator: int
    percentage: float | None
    exclusions: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ProgressSectionEvidence:
    section_id: str
    required: bool
    definition_status: str
    required_fields_complete: int
    required_fields_total: int
    definition_units_complete: int
    definition_units_total: int
    declared_committed_proposals: tuple[str, ...] = ()
    declared_non_committed_proposals: tuple[str, ...] = ()
    heuristic_proposals: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProgressAxis:
    axis_id: str
    status: str
    ratio: ProgressRatio
    basis: str


@dataclass(frozen=True)
class ProjectProgress:
    vertical_id: str
    policy_version: int
    lifecycle_authority_policy_version: int
    definition: ProgressAxis
    evidence: ProgressAxis
    sections: tuple[ProgressSectionEvidence, ...]
    blockers: tuple[Mapping[str, str], ...] = ()
    open_questions: tuple[Mapping[str, str], ...] = ()
    assumptions: tuple[Mapping[str, str], ...] = ()
    warnings: tuple[str, ...] = ()
