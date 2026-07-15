from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence


SOURCE_CATALOG_VERSION = "decision-context-sources-v1"
SCHEMA_VERSION = "decision-context-v1"
EXTRACTOR_VERSION = "decision-context-extractors-v2"
AUTHORITY_POLICY_VERSION = "decision-context-authority-v2"
RELATION_POLICY_VERSION = "decision-context-relations-v2"
LEXICAL_POLICY_VERSION = "decision-context-lexical-v1"
RETRIEVAL_POLICY_VERSION = "decision-context-retrieval-v1"
BUDGET_POLICY_VERSION = "decision-context-budget-v1"


class SourceClassification(StrEnum):
    CANONICAL_SEMANTIC = "canonical_semantic_source"
    GOVERNED_EVIDENCE = "governed_artifact_evidence"
    QUALITY_METADATA = "quality_metadata"
    EXECUTION_METADATA = "execution_state_metadata"
    DERIVED_SIGNAL = "derived_retrieval_signal"
    DERIVED_PROJECTION = "derived_projection"
    GENERATED_OUTPUT = "generated_output"
    DERIVED_INFRASTRUCTURE = "derived_infrastructure"


class SourcePresence(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"


class SourceKind(StrEnum):
    PROPOSAL_BODY = "proposal_body"
    PROPOSAL_DECISION = "proposal_decision"
    RELATED_PROPOSALS = "related_proposals"
    IMPACT_MAP = "impact_map"
    CONFLICT_ANALYSIS = "conflict_analysis"
    ARTIFACT_STATE = "artifact_state"
    READINESS = "readiness"
    QUESTIONS = "questions"
    CONTRIBUTIONS = "contributions"
    PROJECT_CHOICE = "project_choice"
    PROJECT_CHOICE_DECISION = "project_choice_decision"
    PROJECT_CHOICE_LINKS = "project_choice_links"
    PROJECT_CONFLICTS = "project_conflicts"
    CHANGE_SET = "change_set"
    CHANGE_RELATIONS = "change_relations"
    WORK_MANIFEST = "work_manifest"
    VERTICAL_COVERAGE = "vertical_coverage"
    VERTICAL_HEURISTIC = "vertical_heuristic"
    DECISION_PRECEDENTS = "decision_precedents"
    GOVERNANCE_CONSTRAINT = "governance_constraint"
    PROJECT_DEFINITION = "project_definition"


class Canonicality(StrEnum):
    CANONICAL = "canonical"
    GOVERNED_IMPORT = "governed_import"
    DERIVED = "derived"
    LEGACY_UNCLASSIFIED = "legacy_unclassified"


class Authority(StrEnum):
    ACCEPTED_DECISION = "accepted_decision"
    CONDITIONALLY_ACCEPTED_DECISION = "conditionally_accepted_decision"
    DECIDED_PROJECT_CHOICE = "decided_project_choice"
    EXPLICIT_DECISION_PRECEDENT = "explicit_decision_precedent"
    PROJECT_DEFINITION_CONSTRAINT = "project_definition_constraint"
    ACCEPTED_PROPOSAL_CONTEXT = "accepted_proposal_context"
    OWNER_CONFIRMED_EVIDENCE = "owner_confirmed_evidence"
    SYSTEM_STATE = "system_state"
    DRAFT_PROPOSAL = "draft_proposal"
    AGENT_PROPOSED_EVIDENCE = "agent_proposed_evidence"
    PROPOSAL_LOCAL_VOTE = "proposal_local_vote"
    HISTORICAL_PROPOSAL = "historical_proposal"
    HEURISTIC_SIGNAL = "heuristic_signal"
    UNKNOWN = "unknown"


AUTHORITY_RANK: Mapping[Authority, int] = MappingProxyType(
    {
        Authority.ACCEPTED_DECISION: 130,
        Authority.CONDITIONALLY_ACCEPTED_DECISION: 120,
        Authority.DECIDED_PROJECT_CHOICE: 110,
        Authority.EXPLICIT_DECISION_PRECEDENT: 100,
        Authority.PROJECT_DEFINITION_CONSTRAINT: 90,
        Authority.ACCEPTED_PROPOSAL_CONTEXT: 80,
        Authority.OWNER_CONFIRMED_EVIDENCE: 70,
        Authority.SYSTEM_STATE: 60,
        Authority.DRAFT_PROPOSAL: 50,
        Authority.AGENT_PROPOSED_EVIDENCE: 40,
        Authority.PROPOSAL_LOCAL_VOTE: 30,
        Authority.HISTORICAL_PROPOSAL: 20,
        Authority.HEURISTIC_SIGNAL: 10,
        Authority.UNKNOWN: 0,
    }
)


class Activation(StrEnum):
    ACTIVE = "active"
    EXPLORATORY = "exploratory"
    UNRESOLVED = "unresolved"
    HISTORICAL = "historical"
    INACTIVE = "inactive"


class Confidence(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    HEURISTIC = "heuristic"
    UNKNOWN = "unknown"


class Completeness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    ADVISORY = "advisory"
    WARNING = "warning"
    ERROR = "error"


class Freshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class RecordKind(StrEnum):
    PROBLEM = "problem"
    GOAL = "goal"
    NON_GOAL = "non_goal"
    PROPOSAL_CLAIM = "proposal_claim"
    ACCEPTANCE_CRITERION = "acceptance_criterion"
    PROPOSAL_STATE = "proposal_state"
    DECISION_STATE = "decision_state"
    DECISION_REASON = "decision_reason"
    DECISION_QUALIFIER = "decision_qualifier"
    DECISION_STATEMENT = "decision_statement"
    CONSTRAINT = "constraint"
    PRECEDENT = "precedent"
    EVENT = "event"
    EXECUTION_STATE = "execution_state"


class NodeType(StrEnum):
    PROPOSAL = "proposal"
    DECISION = "decision"
    CHOICE = "choice"
    CHANGE = "change"
    WORK = "work"
    VERTICAL_SECTION = "vertical_section"
    CAPABILITY = "capability"
    SURFACE = "surface"
    FEATURE = "feature"
    COMMAND = "command"
    FILE = "file"


class RelationType(StrEnum):
    INCLUDES = "includes"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    CONFLICTS_WITH = "conflicts_with"
    SUPERSEDES = "supersedes"
    MERGED_INTO = "merged_into"
    SPLIT_INTO = "split_into"
    IMPLEMENTS = "implements"
    SELECTED_BY = "selected_by"
    AFFECTS_CAPABILITY = "affects_capability"
    AFFECTS_SURFACE = "affects_surface"
    AFFECTS_FEATURE = "affects_feature"
    TOUCHES_COMMAND = "touches_command"
    TOUCHES_FILE = "touches_file"
    MAPS_TO_VERTICAL_SECTION = "maps_to_vertical_section"
    DERIVED_FROM = "derived_from"


class ContextBudget(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"


@dataclass(frozen=True)
class SourceSpan:
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ParsedFragment:
    fragment_id: str
    anchor: str
    occurrence: int
    label: str
    text: str
    text_sha256: str
    span: SourceSpan | None = None
    completeness: Completeness = Completeness.COMPLETE


@dataclass(frozen=True)
class DecisionContextDiagnostic:
    diagnostic_id: str
    code: str
    severity: DiagnosticSeverity
    fatal: bool
    message: str
    source_path: str = ""
    fragment_id: str = ""
    target_id: str = ""
    recovery: str = ""
    snippet: str = ""


@dataclass(frozen=True)
class SourceDocument:
    path: str
    owner_id: str
    source_kind: SourceKind
    classification: SourceClassification
    presence: SourcePresence
    sha256: str | None
    completeness: Completeness
    frontmatter: Mapping[str, object]
    fragments: tuple[ParsedFragment, ...]
    diagnostic_ids: tuple[str, ...] = ()
    _content: bytes | None = None


@dataclass(frozen=True)
class DecisionContextEvidence:
    evidence_id: str
    source_path: str
    source_sha256: str
    source_kind: SourceKind
    fragment_id: str
    fragment_label: str
    span: SourceSpan | None
    canonicality: Canonicality
    authority: Authority
    activation: Activation
    confidence: Confidence
    completeness: Completeness


@dataclass(frozen=True)
class DecisionContextRecord:
    record_id: str
    kind: RecordKind
    owner_type: NodeType
    owner_id: str
    activation: Activation
    authority: Authority
    text: str
    text_sha256: str
    evidence_ids: tuple[str, ...]
    related_record_ids: tuple[str, ...] = ()
    applicability_tokens: tuple[str, ...] = ()
    diagnostic_ids: tuple[str, ...] = ()
    canonical_date: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class DecisionContextNode:
    node_id: str
    node_type: NodeType
    label: str
    existence: str = "cataloged"


@dataclass(frozen=True)
class DecisionContextRelation:
    relation_id: str
    source_id: str
    source_type: NodeType
    target_id: str
    target_type: NodeType
    relation_type: RelationType
    scope: str
    activation: Activation
    authority: Authority
    confidence: Confidence
    evidence_ids: tuple[str, ...]
    diagnostic_ids: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class RetrievalReason:
    signal: str
    contribution: int
    detail: str


@dataclass(frozen=True)
class RetrievalHit:
    owner_id: str
    owner_type: NodeType
    score: int
    activation: Activation
    authority: Authority
    selected_record_ids: tuple[str, ...]
    selected_relation_ids: tuple[str, ...]
    decisions: tuple[str, ...]
    constraints: tuple[str, ...]
    non_goals: tuple[str, ...]
    claims: tuple[str, ...]
    reasons: tuple[RetrievalReason, ...]
    evidence_ids: tuple[str, ...]
    canonical_date: str = ""


@dataclass(frozen=True)
class RetrievalRequest:
    budget: ContextBudget
    target_id: str = ""
    idea_text: str = ""


@dataclass(frozen=True)
class RetrievalPolicy:
    version: str
    candidate_limit: int
    minimum_score: int
    historical_threshold: int
    score_minimum: int
    score_maximum: int
    signal_weights: Mapping[str, int]
    signal_caps: Mapping[str, int]


@dataclass(frozen=True)
class BudgetPolicy:
    version: str
    budget: ContextBudget
    max_hits: int
    max_records: int
    max_relations: int
    max_reasons_per_hit: int
    transitive_depth: int
    max_serialized_bytes: int


@dataclass(frozen=True)
class TruncationMetadata:
    truncated: bool
    original_counts: Mapping[str, int]
    retained_counts: Mapping[str, int]


@dataclass(frozen=True)
class DecisionContextPacket:
    schema_version: str
    retrieval_policy_version: str
    budget_policy_version: str
    budget: ContextBudget
    source_fingerprint_sha256: str
    semantic_fingerprint_sha256: str
    completeness: Completeness
    hits: tuple[RetrievalHit, ...]
    evidence: tuple[DecisionContextEvidence, ...]
    diagnostics: tuple[DecisionContextDiagnostic, ...]
    truncation: TruncationMetadata
    empty_reason: str = ""


@dataclass(frozen=True)
class DecisionContextManifest:
    schema_version: str
    generator_version: str
    source_catalog_version: str
    extractor_version: str
    authority_policy_version: str
    relation_policy_version: str
    retrieval_policy_version: str
    budget_policy_version: str
    source_fingerprint_sha256: str
    semantic_fingerprint_sha256: str
    generated_at: str
    inputs: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class DecisionContextFreshnessCheck:
    status: Freshness
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SourceAccessStats:
    discovery_passes: int
    reads: Mapping[str, int]
    hashes: Mapping[str, int]
    parses: Mapping[str, int]


@dataclass(frozen=True)
class ExtractionSession:
    source_catalog_version: str
    source_fingerprint_sha256: str
    completeness: Completeness
    sources: tuple[SourceDocument, ...]
    diagnostics: tuple[DecisionContextDiagnostic, ...]
    access_stats: SourceAccessStats


@dataclass(frozen=True)
class DecisionContextIndex:
    schema_version: str
    source_catalog_version: str
    extractor_version: str
    authority_policy_version: str
    relation_policy_version: str
    source_fingerprint_sha256: str
    semantic_fingerprint_sha256: str
    completeness: Completeness
    sources: tuple[SourceDocument, ...]
    evidence: tuple[DecisionContextEvidence, ...]
    records: tuple[DecisionContextRecord, ...]
    nodes: tuple[DecisionContextNode, ...]
    relations: tuple[DecisionContextRelation, ...]
    diagnostics: tuple[DecisionContextDiagnostic, ...]
    access_stats: SourceAccessStats
    records_by_owner: Mapping[str, tuple[str, ...]]
    incoming_relations: Mapping[str, tuple[str, ...]]
    outgoing_relations: Mapping[str, tuple[str, ...]]
    token_postings: Mapping[str, tuple[str, ...]]
    domain_postings: Mapping[str, tuple[str, ...]]
    owner_authority: Mapping[str, Authority]
    owner_activation: Mapping[str, Activation]

    def record_map(self) -> Mapping[str, DecisionContextRecord]:
        return MappingProxyType({record.record_id: record for record in self.records})

    def relation_map(self) -> Mapping[str, DecisionContextRelation]:
        return MappingProxyType({relation.relation_id: relation for relation in self.relations})

    def evidence_map(self) -> Mapping[str, DecisionContextEvidence]:
        return MappingProxyType({item.evidence_id: item for item in self.evidence})


def freeze_mapping(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(values))


def freeze_string_tuple_mapping(values: Mapping[str, Sequence[str]]) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType({key: tuple(items) for key, items in values.items()})


def to_json_ready(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {
            field.name: to_json_ready(getattr(value, field.name))
            for field in fields(value)
            if not field.name.startswith("_")
        }
    if isinstance(value, Mapping):
        return {str(key): to_json_ready(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [to_json_ready(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [to_json_ready(item) for item in sorted(value, key=str)]
    raise TypeError(f"Unsupported decision-context serialization value: {type(value).__name__}")
