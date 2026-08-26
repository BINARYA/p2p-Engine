from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Sequence

from p2p_engine.core.mutation_preview import canonical_json_bytes, semantic_sha256


PROJECT_READINESS_CONTRACT = "p2p-project-readiness/v2"
PROJECT_READINESS_ALGORITHM_VERSION = "project-structure-readiness-v2.0"
PROJECT_READINESS_GAP_POLICY_VERSION = 1
PROJECT_READINESS_CURSOR_POLICY_VERSION = 1
PROJECT_READINESS_DEFAULT_PAGE_SIZE = 20
PROJECT_READINESS_MAX_PAGE_SIZE = 100
PROJECT_READINESS_REVIEW_DETAIL_LIMIT = 10
PROJECT_READINESS_DEFAULT_PAYLOAD_BYTES = 64 * 1024
PROJECT_READINESS_NEUTRAL_DEPENDENCY_RANK = 100


class ProjectReadinessGapKind(StrEnum):
    INTEGRITY_BLOCKER = "integrity_blocker"
    COMPATIBILITY_BLOCKER = "compatibility_blocker"
    AUTHORITY_BLOCKER = "authority_blocker"
    OWNER_DECISION_BLOCKER = "owner_decision_blocker"
    ANSWERED_NOT_APPLIED = "answered_not_applied"
    INCOMPLETE_REQUIRED_DEFINITION = "incomplete_required_definition"
    ASSUMPTION_TO_VALIDATE = "assumption_to_validate"
    OPTIONAL_DECLARED_EVIDENCE = "optional_declared_evidence"
    UNMAPPED_PROPOSAL_COVERAGE = "unmapped_proposal_coverage"


class ProjectReadinessGapSeverity(StrEnum):
    BLOCKER = "blocker"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


_CLASS_RANKS = {
    ProjectReadinessGapKind.INTEGRITY_BLOCKER: 1,
    ProjectReadinessGapKind.COMPATIBILITY_BLOCKER: 1,
    ProjectReadinessGapKind.AUTHORITY_BLOCKER: 1,
    ProjectReadinessGapKind.OWNER_DECISION_BLOCKER: 1,
    ProjectReadinessGapKind.ANSWERED_NOT_APPLIED: 2,
    ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION: 3,
    ProjectReadinessGapKind.ASSUMPTION_TO_VALIDATE: 4,
    ProjectReadinessGapKind.OPTIONAL_DECLARED_EVIDENCE: 5,
    ProjectReadinessGapKind.UNMAPPED_PROPOSAL_COVERAGE: 6,
}


@dataclass(frozen=True)
class ProjectReadinessSnapshotIdentity:
    fingerprint: str
    workspace_schema_version: int
    workspace_schema_state: str
    vertical_id: str
    vertical_version: str
    vertical_lock_checksum: str
    profile: str
    modules: tuple[str, ...]
    source_hashes: Mapping[str, str]
    policy_versions: Mapping[str, int]
    contract_version: str = PROJECT_READINESS_CONTRACT
    algorithm_version: str = PROJECT_READINESS_ALGORITHM_VERSION
    structure_id: str = ""
    structure_revision: int = 0
    structure_checksum: str = ""
    memory_revision: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "fingerprint": self.fingerprint,
            "algorithm_version": self.algorithm_version,
            "workspace_schema_version": self.workspace_schema_version,
            "workspace_schema_state": self.workspace_schema_state,
            "structure": {
                "id": self.structure_id,
                "revision": self.structure_revision,
                "checksum": self.structure_checksum,
            },
            "memory_revision": self.memory_revision,
            "vertical_id": self.vertical_id,
            "vertical_version": self.vertical_version,
            "vertical_lock_checksum": self.vertical_lock_checksum,
            "profile": self.profile,
            "modules": list(self.modules),
            "source_hashes": dict(self.source_hashes),
            "policy_versions": dict(self.policy_versions),
        }


@dataclass(frozen=True)
class ProjectReadinessAssumptionSnapshot:
    assumption_id: str
    status: str
    field_id: str = ""
    dependency_rank: int = PROJECT_READINESS_NEUTRAL_DEPENDENCY_RANK


@dataclass(frozen=True)
class ProjectReadinessQuestionSnapshot:
    question_id: str
    revision: int
    state: str
    target_kind: str
    target_id: str
    applicability: str = "applicable"


@dataclass(frozen=True)
class ProjectReadinessRatio:
    numerator: float
    denominator: float
    score: float | None
    unit: str = "weight"
    exclusions: Mapping[str, float | int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "numerator": _compact_number(self.numerator),
            "denominator": _compact_number(self.denominator),
            "score": self.score,
            "unit": self.unit,
            "exclusions": {
                key: _compact_number(value)
                for key, value in sorted(self.exclusions.items())
            },
        }


@dataclass(frozen=True)
class ProjectReadinessAxis:
    axis_id: str
    status: str
    ratio: ProjectReadinessRatio
    basis: str
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "axis_id": self.axis_id,
            "status": self.status,
            "ratio": self.ratio.to_dict(),
            "basis": self.basis,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class ProjectReadinessCriterionSnapshot:
    criterion_id: str
    section_id: str
    title: str
    weight: float
    evaluation: str
    required: bool
    status: str
    definition_status: str
    evidence_item_ids: tuple[str, ...] = ()
    not_applicable_reason: str = ""

    @property
    def applicable(self) -> bool:
        return self.status != "not_applicable"

    @property
    def satisfied(self) -> bool:
        return self.status == "satisfied"

    def to_dict(self) -> dict[str, object]:
        return {
            "criterion_id": self.criterion_id,
            "section_id": self.section_id,
            "title": self.title,
            "weight": _compact_number(self.weight),
            "evaluation": self.evaluation,
            "required": self.required,
            "status": self.status,
            "definition_status": self.definition_status,
            "evidence_item_ids": list(self.evidence_item_ids),
            "not_applicable_reason": self.not_applicable_reason,
        }


@dataclass(frozen=True)
class ProjectReadinessSectionSnapshot:
    section_id: str
    title: str
    required: bool
    priority: int
    definition_status: str
    missing_required_fields: tuple[str, ...] = ()
    assumptions: tuple[ProjectReadinessAssumptionSnapshot, ...] = ()
    open_blocker_ids: tuple[str, ...] = ()
    declared_proposals: tuple[str, ...] = ()
    active_declared_proposals: tuple[str, ...] = ()
    heuristic_proposals: tuple[str, ...] = ()
    declared_questions: tuple[str, ...] = ()
    question_states: tuple[ProjectReadinessQuestionSnapshot, ...] = ()
    criteria: tuple[ProjectReadinessCriterionSnapshot, ...] = ()
    active_weight: float = 0.0
    applicable_weight: float = 0.0
    satisfied_weight: float = 0.0
    evidence_weight: float = 0.0
    definition_score: float | None = None
    evidence_score: float | None = None
    readiness_status: str = "not_configured"


@dataclass(frozen=True)
class ProjectReadinessSnapshot:
    identity: ProjectReadinessSnapshotIdentity
    definition_valid: bool
    definition_exists: bool
    fallback_used: bool
    vertical_source: str
    sections: tuple[ProjectReadinessSectionSnapshot, ...]
    unmapped_proposals: tuple[str, ...]
    owner_available: bool = True
    diagnostics: tuple["ProjectReadinessDiagnostic", ...] = ()
    contract_version: str = PROJECT_READINESS_CONTRACT
    algorithm_version: str = PROJECT_READINESS_ALGORITHM_VERSION
    status: str = "calculated"
    definition: ProjectReadinessAxis | None = None
    evidence: ProjectReadinessAxis | None = None
    actions: tuple[str, ...] = ()
    memory_classification_status: str = "unknown"


@dataclass(frozen=True)
class ProjectReadinessDiagnostic:
    code: str
    severity: str
    message: str
    suggested_command: str = ""
    section_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "suggested_command": self.suggested_command,
            "section_id": self.section_id,
        }


@dataclass(frozen=True)
class ProjectReadinessGap:
    gap_id: str
    identity_sha256: str
    snapshot_fingerprint: str
    vertical_id: str
    vertical_version: str
    vertical_lock_checksum: str
    section_id: str
    target_kind: str
    target_id: str
    kind: ProjectReadinessGapKind
    severity: ProjectReadinessGapSeverity
    applicability: str
    definition_status: str
    missing_fields: tuple[str, ...]
    declared_evidence: tuple[str, ...]
    heuristic_suggestions: tuple[str, ...]
    required_authority: str
    owner_input_required: bool
    question_id: str
    question_revision: int | None
    next_operation: str
    rationale: str
    priority_class: int
    priority_policy_version: int
    priority_rationale: str
    tie_break: tuple[object, ...]
    dependency_rank: int = PROJECT_READINESS_NEUTRAL_DEPENDENCY_RANK

    def to_dict(self) -> dict[str, object]:
        return {
            "gap_id": self.gap_id,
            "identity_sha256": self.identity_sha256,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "vertical_id": self.vertical_id,
            "vertical_version": self.vertical_version,
            "vertical_lock_checksum": self.vertical_lock_checksum,
            "section_id": self.section_id,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "kind": self.kind.value,
            "severity": self.severity.value,
            "applicability": self.applicability,
            "definition_status": self.definition_status,
            "missing_fields": list(self.missing_fields),
            "declared_evidence": list(self.declared_evidence),
            "heuristic_suggestions": list(self.heuristic_suggestions),
            "required_authority": self.required_authority,
            "owner_input_required": self.owner_input_required,
            "question_id": self.question_id,
            "question_revision": self.question_revision,
            "next_operation": self.next_operation,
            "rationale": self.rationale,
            "priority": {
                "class": self.priority_class,
                "policy_version": self.priority_policy_version,
                "rationale": self.priority_rationale,
                "tie_break": list(self.tie_break),
                "dependency_rank": self.dependency_rank,
            },
        }


@dataclass(frozen=True)
class ProjectReadinessResult:
    snapshot: ProjectReadinessSnapshotIdentity
    gaps: tuple[ProjectReadinessGap, ...]
    diagnostics: tuple[ProjectReadinessDiagnostic, ...]
    counts: Mapping[str, int]
    status: str = "calculated"
    definition: ProjectReadinessAxis | None = None
    evidence: ProjectReadinessAxis | None = None
    sections: tuple[ProjectReadinessSectionSnapshot, ...] = ()
    actions: tuple[str, ...] = ()
    contract_version: str = PROJECT_READINESS_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "status": self.status,
            "snapshot": self.snapshot.to_dict(),
            "definition": self.definition.to_dict() if self.definition else None,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "sections": [_section_to_dict(item) for item in self.sections],
            "gaps": [item.to_dict() for item in self.gaps],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "counts": dict(self.counts),
            "actions": list(self.actions),
        }


@dataclass(frozen=True)
class ProjectReadinessCursor:
    collection: str
    snapshot_fingerprint: str
    policy_version: int
    last_key: tuple[object, ...]

    def encode(self) -> str:
        body = {
            "collection": self.collection,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "policy_version": self.policy_version,
            "last_key": list(self.last_key),
        }
        envelope = {"body": body, "checksum": semantic_sha256(body)}
        return base64.urlsafe_b64encode(canonical_json_bytes(envelope)).decode("ascii").rstrip("=")

    @classmethod
    def decode(cls, value: str) -> "ProjectReadinessCursor":
        try:
            padding = "=" * (-len(value) % 4)
            envelope = json.loads(base64.urlsafe_b64decode(value + padding).decode("utf-8"))
            body = envelope["body"]
            checksum = envelope["checksum"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid readiness cursor. Restart pagination without a cursor.") from exc
        if not isinstance(body, dict) or semantic_sha256(body) != checksum:
            raise ValueError("Invalid readiness cursor checksum. Restart pagination without a cursor.")
        try:
            return cls(
                collection=str(body["collection"]),
                snapshot_fingerprint=str(body["snapshot_fingerprint"]),
                policy_version=int(body["policy_version"]),
                last_key=tuple(body["last_key"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid readiness cursor payload. Restart pagination without a cursor.") from exc


@dataclass(frozen=True)
class ProjectReadinessPage:
    collection: str
    snapshot_fingerprint: str
    items: tuple[object, ...]
    total: int
    limit: int
    next_cursor: str = ""
    truncated: bool = False
    payload_bytes: int = 0
    diagnostics: tuple[ProjectReadinessDiagnostic, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        def serialize(item: object) -> object:
            to_dict = getattr(item, "to_dict", None)
            return to_dict() if callable(to_dict) else item

        return {
            "collection": self.collection,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "items": [serialize(item) for item in self.items],
            "total": self.total,
            "limit": self.limit,
            "next_cursor": self.next_cursor,
            "truncated": self.truncated,
            "payload_bytes": self.payload_bytes,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


def readiness_snapshot_identity(
    *,
    workspace_schema_version: int,
    workspace_schema_state: str,
    vertical_id: str,
    vertical_version: str,
    vertical_lock_checksum: str,
    profile: str,
    modules: Sequence[str],
    source_hashes: Mapping[str, str],
    policy_versions: Mapping[str, int],
    structure_id: str = "",
    structure_revision: int = 0,
    structure_checksum: str = "",
    memory_revision: str = "",
    algorithm_version: str = PROJECT_READINESS_ALGORITHM_VERSION,
    contract_version: str = PROJECT_READINESS_CONTRACT,
) -> ProjectReadinessSnapshotIdentity:
    payload = {
        "contract_version": contract_version,
        "algorithm_version": algorithm_version,
        "workspace_schema_version": workspace_schema_version,
        "workspace_schema_state": workspace_schema_state,
        "structure_id": structure_id,
        "structure_revision": structure_revision,
        "structure_checksum": structure_checksum,
        "memory_revision": memory_revision,
        "vertical_id": vertical_id,
        "vertical_version": vertical_version,
        "vertical_lock_checksum": vertical_lock_checksum,
        "profile": profile,
        "modules": sorted(str(item) for item in modules),
        "source_hashes": {key: source_hashes[key] for key in sorted(source_hashes)},
        "policy_versions": {key: policy_versions[key] for key in sorted(policy_versions)},
    }
    return ProjectReadinessSnapshotIdentity(
        fingerprint=semantic_sha256(payload),
        workspace_schema_version=workspace_schema_version,
        workspace_schema_state=workspace_schema_state,
        vertical_id=vertical_id,
        vertical_version=vertical_version,
        vertical_lock_checksum=vertical_lock_checksum,
        profile=profile,
        modules=tuple(sorted(str(item) for item in modules)),
        source_hashes=dict(sorted(source_hashes.items())),
        policy_versions=dict(sorted(policy_versions.items())),
        contract_version=contract_version,
        algorithm_version=algorithm_version,
        structure_id=structure_id,
        structure_revision=structure_revision,
        structure_checksum=structure_checksum,
        memory_revision=memory_revision,
    )


def readiness_gap_identity(
    *,
    vertical_id: str,
    section_id: str,
    kind: ProjectReadinessGapKind,
    target_kind: str,
    target_id: str,
    policy_major: int = PROJECT_READINESS_GAP_POLICY_VERSION,
) -> tuple[str, str]:
    payload = {
        "vertical_id": vertical_id,
        "section_id": section_id,
        "kind": kind.value,
        "target_kind": target_kind,
        "target_id": target_id,
        "policy_major": policy_major,
    }
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"PGAP-{digest[:16]}", digest


def readiness_class_rank(kind: ProjectReadinessGapKind) -> int:
    return _CLASS_RANKS[kind]


def _section_to_dict(section: ProjectReadinessSectionSnapshot) -> dict[str, object]:
    return {
        "section_id": section.section_id,
        "title": section.title,
        "required": section.required,
        "priority": section.priority,
        "definition_status": section.definition_status,
        "missing_required_fields": list(section.missing_required_fields),
        "declared_proposals": list(section.declared_proposals),
        "active_declared_proposals": list(section.active_declared_proposals),
        "heuristic_proposals": list(section.heuristic_proposals),
        "declared_questions": list(section.declared_questions),
        "criteria": [item.to_dict() for item in section.criteria],
        "active_weight": _compact_number(section.active_weight),
        "applicable_weight": _compact_number(section.applicable_weight),
        "satisfied_weight": _compact_number(section.satisfied_weight),
        "evidence_weight": _compact_number(section.evidence_weight),
        "definition_score": section.definition_score,
        "evidence_score": section.evidence_score,
        "readiness_status": section.readiness_status,
    }


def _compact_number(value: float | int) -> float | int:
    numeric = float(value)
    return int(numeric) if numeric.is_integer() else numeric
