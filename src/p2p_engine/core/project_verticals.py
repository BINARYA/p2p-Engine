from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class VerticalSection:
    section_id: str
    title: str
    purpose: str
    required: bool = True
    priority: int = 100


@dataclass(frozen=True)
class VerticalRubric:
    rubric_id: str
    title: str
    section_id: str
    required: bool = True
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalQuestion:
    question_id: str
    section_id: str
    question: str
    priority: str = "medium"
    rationale: str = ""


@dataclass(frozen=True)
class VerticalArtifact:
    artifact_id: str
    title: str
    section_ids: list[str] = field(default_factory=list)
    required: bool = False


@dataclass(frozen=True)
class VerticalPack:
    vertical_id: str
    name: str
    version: str
    description: str
    extends: str | None
    source: str
    path: Path | None
    sections: list[VerticalSection]
    rubrics: list[VerticalRubric]
    questions: list[VerticalQuestion]
    artifacts: list[VerticalArtifact]
    profiles: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalListItem:
    vertical_id: str
    name: str
    version: str
    source: str
    active: bool
    path: Path | None


@dataclass(frozen=True)
class ActiveProjectVertical:
    vertical_id: str
    source: str
    path: Path | None
    selected_at: str = ""
    selected_by: str = ""
    fallback_used: bool = False


@dataclass(frozen=True)
class VerticalValidationIssue:
    severity: str
    field: str
    message: str


@dataclass(frozen=True)
class VerticalValidationResult:
    target: str
    valid: bool
    vertical_id: str
    source: str
    issues: list[VerticalValidationIssue]


@dataclass(frozen=True)
class CustomVerticalCandidate:
    source_idea: str
    pack: VerticalPack
    base_project_sections_reused: list[str]
    vertical_specific_additions: list[str]
    yaml_text: str


@dataclass(frozen=True)
class ProjectVerticalAddResult:
    vertical_id: str
    path: Path
    activated: bool


@dataclass(frozen=True)
class ProposalVerticalCoverageSection:
    section_id: str
    relevance: str
    rationale: str
    source: str = "declared"


@dataclass(frozen=True)
class ProposalVerticalCoverage:
    proposal_id: str
    vertical_id: str
    sections: list[ProposalVerticalCoverageSection]
    path: Path | None = None


@dataclass(frozen=True)
class VerticalSectionReview:
    section_id: str
    title: str
    status: str
    proposals: list[str]
    gaps: list[str]
    risks: list[str]
    questions: list[str]


@dataclass(frozen=True)
class ProjectReadinessReview:
    active_vertical_id: str
    vertical_source: str
    fallback_used: bool
    sections: list[VerticalSectionReview]
    unmapped_proposals: list[str]
    missing_capisaldi: list[str]
    generated_questions: list[str]
    suggested_next: list[str]
