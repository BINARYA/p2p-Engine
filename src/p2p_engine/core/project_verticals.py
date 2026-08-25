from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from p2p_engine.core.project_domain import ProjectDomainRef
from p2p_engine.core.project_readiness import ProjectReadinessDiagnostic, ProjectReadinessGap


@dataclass(frozen=True)
class VerticalSection:
    section_id: str
    title: str
    purpose: str
    required: bool = True
    priority: int = 100
    fields: list["VerticalField"] = field(default_factory=list)
    completion_policy: "VerticalCompletionPolicy | None" = None


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
    target_kind: str = ""
    target_id: str = ""
    answer_contract: dict[str, object] = field(default_factory=dict)
    fallback_key: str = ""
    aliases: tuple[str, ...] = ()
    deferred_trigger: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VerticalArtifact:
    artifact_id: str
    title: str
    section_ids: list[str] = field(default_factory=list)
    required: bool = False


@dataclass(frozen=True)
class VerticalField:
    field_id: str
    label: str
    required: bool = True
    question: str = ""
    assisted_answer: str = ""
    completion_criteria: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    suggested_artifacts: list[str] = field(default_factory=list)
    maturity_gates: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalCompletionPolicy:
    allow_assumed_completion: bool = False
    required_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalManifest:
    vertical_id: str
    name: str
    version: str
    schema_version: int = 3
    publisher: str = ""
    source: str = ""
    compatibility: dict[str, object] = field(default_factory=dict)
    license_id: str = ""
    lineage: dict[str, str] = field(default_factory=dict)
    dependencies: list["VerticalDependency"] = field(default_factory=list)
    primary_domain: ProjectDomainRef | None = None
    domain_tags: tuple[str, ...] = ()

    @property
    def coordinate(self) -> str:
        if not self.publisher or not self.vertical_id or not self.version:
            return ""
        return f"{self.publisher}/{self.vertical_id}@{self.version}"


@dataclass(frozen=True)
class VerticalDependency:
    coordinate: str
    checksum: str


@dataclass(frozen=True)
class VerticalProfile:
    profile_id: str
    title: str
    description: str = ""
    enabled_modules: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalModule:
    module_id: str
    title: str
    description: str = ""
    section_ids: list[str] = field(default_factory=list)


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
    schema_version: int = 3
    manifest: VerticalManifest | None = None
    profile_specs: list[VerticalProfile] = field(default_factory=list)
    module_specs: list[VerticalModule] = field(default_factory=list)
    compatibility: dict[str, object] = field(default_factory=dict)

    @property
    def coordinate(self) -> str:
        return self.manifest.coordinate if self.manifest else ""


@dataclass(frozen=True)
class VerticalListItem:
    vertical_id: str
    name: str
    version: str
    source: str
    active: bool
    path: Path | None
    coordinate: str = ""


@dataclass(frozen=True)
class ActiveProjectVertical:
    vertical_id: str
    source: str
    path: Path | None
    selected_at: str = ""
    selected_by: str = ""
    fallback_used: bool = False
    coordinate: str = ""
    reconciliation_required: bool = False
    reconciliation_command: str = ""
    derived_updates: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VerticalReadState:
    active: ActiveProjectVertical
    pack: "VerticalPack"
    valid_section_ids: frozenset[str]
    terms_by_section: Mapping[str, tuple[str, ...]]
    term_frequency: Mapping[str, int]
    base_section_ids: frozenset[str] = frozenset()
    readiness_terms_by_section: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class VerticalPackSource:
    source_type: str
    resolved_from: str
    path: Path | None = None
    package: str = ""


@dataclass(frozen=True)
class ResolvedVerticalPack:
    pack: VerticalPack
    source: VerticalPackSource
    checksum: str


@dataclass(frozen=True)
class VerticalLock:
    vertical_id: str
    name: str
    version: str
    pack_schema_version: int
    source: VerticalPackSource
    checksum: str
    compatibility: dict[str, object] = field(default_factory=dict)
    selected_at: str = ""
    selected_by: str = ""
    trust: dict[str, object] = field(default_factory=dict)
    path: Path | None = None
    coordinate: str = ""
    artifact_checksum: str = ""
    dependencies: list[VerticalDependency] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalLockStatus:
    status: str
    path: Path
    locked: VerticalLock | None = None
    resolved: ResolvedVerticalPack | None = None
    message: str = ""
    suggested_command: str = ""


@dataclass(frozen=True)
class VerticalValidationIssue:
    severity: str
    field: str
    message: str
    code: str = ""


@dataclass(frozen=True)
class VerticalValidationResult:
    target: str
    valid: bool
    vertical_id: str
    source: str
    issues: list[VerticalValidationIssue]


@dataclass(frozen=True)
class VerticalMigrationCandidate:
    vertical_id: str
    profile: str
    modules: tuple[str, ...]
    checksum: str
    candidate_files: dict[str, bytes]
    reconciliation_required: bool = False
    reference: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "vertical_id": self.vertical_id,
            "profile": self.profile,
            "modules": list(self.modules),
            "checksum": self.checksum,
            "reference": self.reference or self.vertical_id,
            "candidate_paths": sorted(self.candidate_files),
        }


@dataclass(frozen=True)
class ProjectDefinitionFieldValue:
    field_id: str
    value: object
    source: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ProjectDefinitionAssumption:
    assumption_id: str
    text: str
    status: str = "to_validate"
    field_id: str = ""


@dataclass(frozen=True)
class ProjectDefinitionBlocker:
    blocker_id: str
    text: str
    status: str = "open"


@dataclass
class ProjectDefinitionSectionState:
    section_id: str
    status: str = "missing"
    fields: dict[str, ProjectDefinitionFieldValue] = field(default_factory=dict)
    missing_required_fields: list[str] = field(default_factory=list)
    assumptions: list[ProjectDefinitionAssumption] = field(default_factory=list)
    blockers: list[ProjectDefinitionBlocker] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectDefinitionHistoryEntry:
    at: str
    actor: str
    operation: str
    section_id: str = ""


@dataclass(frozen=True)
class ProjectDefinitionOrphan:
    orphan_id: str
    source_vertical: str
    source_section_id: str
    source_field_id: str
    value: object
    source: str = ""
    updated_at: str = ""
    reason: str = "unmapped"
    target_vertical: str = ""


@dataclass(frozen=True)
class ProjectDefinitionState:
    schema_version: int
    vertical_id: str
    vertical_version: str
    profile: str = "default"
    modules: list[str] = field(default_factory=list)
    lock_checksum: str = ""
    sections: list[ProjectDefinitionSectionState] = field(default_factory=list)
    next_suggested_action: dict[str, object] = field(default_factory=dict)
    history: list[ProjectDefinitionHistoryEntry] = field(default_factory=list)
    orphans: list[ProjectDefinitionOrphan] = field(default_factory=list)
    structure_id: str = ""
    structure_revision: int = 0
    structure_checksum: str = ""
    path: Path | None = None


@dataclass(frozen=True)
class ProjectDefinitionPatch:
    actor: str
    operations: list[dict[str, object]]
    schema_version: int = 1


@dataclass(frozen=True)
class ProjectDefinitionPatchResult:
    state: ProjectDefinitionState
    path: Path
    operations_applied: int
    derived_updates: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDefinitionCandidate:
    state: ProjectDefinitionState
    payload: dict[str, object]
    semantic_payload: dict[str, object]
    candidate_bytes: bytes
    semantic_sha256: str
    operation_ids: tuple[str, ...]
    changed_sections: tuple[str, ...]


@dataclass(frozen=True)
class ProjectDefinitionView:
    exists: bool
    valid: bool
    path: Path
    state: ProjectDefinitionState | None = None
    issues: list[VerticalValidationIssue] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectVerticalContext:
    active: ActiveProjectVertical
    lock_status: VerticalLockStatus
    selected_profile: str
    enabled_modules: list[str]
    rubric_summary: dict[str, object]
    definition_summary: dict[str, object]
    warnings: list[str] = field(default_factory=list)
    next_suggested_action: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposalVerticalCoverageSection:
    section_id: str
    relevance: str
    rationale: str
    source: str = "declared"
    provenance: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposalVerticalCoverage:
    proposal_id: str
    vertical_id: str
    sections: list[ProposalVerticalCoverageSection]
    path: Path | None = None
    schema_version: int = 2
    provenance: dict[str, object] = field(default_factory=dict)
    authority: str = "unverified"


@dataclass(frozen=True)
class ProposalVerticalCoverageStatus:
    proposal_id: str
    state: str
    path: Path
    coverage: ProposalVerticalCoverage | None = None
    message: str = ""


@dataclass(frozen=True)
class VerticalCoverageSuggestionSection:
    section_id: str
    confidence: float
    evidence: list[dict[str, object]]
    reasons: list[str]


@dataclass(frozen=True)
class ProposalVerticalCoverageSuggestion:
    proposal_id: str
    vertical_id: str
    policy_version: int
    candidates: list[VerticalCoverageSuggestionSection]
    suppressed_sections: list[str]
    source_paths: list[Path]


@dataclass(frozen=True)
class VerticalSectionReview:
    section_id: str
    title: str
    status: str
    proposals: list[str]
    gaps: list[str]
    risks: list[str]
    questions: list[str]
    declared_proposals: list[str] = field(default_factory=list)
    heuristic_proposals: list[str] = field(default_factory=list)
    definition_status: str = "not_initialized"


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
    definition_valid: bool = False
    heuristic_mappings: dict[str, list[str]] = field(default_factory=dict)
    snapshot_fingerprint: str = ""
    gaps: list[ProjectReadinessGap] = field(default_factory=list)
    gap_counts: dict[str, int] = field(default_factory=dict)
    diagnostics: list[ProjectReadinessDiagnostic] = field(default_factory=list)
    unmapped_proposals_total: int = 0
    unmapped_proposals_truncated: bool = False
    generated_questions_total: int = 0
    generated_questions_truncated: bool = False
