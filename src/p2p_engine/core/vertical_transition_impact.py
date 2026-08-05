from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Generic, Iterable, TypeVar

from p2p_engine.core.mutation_preview import semantic_sha256


VERTICAL_TRANSITION_IMPACT_CONTRACT = "p2p-vertical-transition-impact/v1"
VERTICAL_TRANSITION_COLLECTION_LIMIT = 128
VERTICAL_TRANSITION_TOTAL_ITEM_LIMIT = 512

_DOMAIN_REFERENCE = re.compile(
    r"^(?:definition_field:[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    r"|definition_(?:assumption|blocker):[A-Za-z0-9_-]+/[A-Za-z0-9_-]+"
    r"|definition_orphan:[A-Za-z0-9_-]+"
    r"|rubric:[A-Za-z0-9_-]+"
    r"|question:[A-Za-z0-9_-]+"
    r"|artifact:(?:vertical|lock|definition|rubrics|questions))$"
)


class TransitionOperation(str, Enum):
    INSTALL = "install"
    ADOPT = "adopt"
    MIGRATE = "migrate"


class EvidenceKind(str, Enum):
    DEFINITION_FIELD = "definition_field"
    DEFINITION_ASSUMPTION = "definition_assumption"
    DEFINITION_BLOCKER = "definition_blocker"
    DEFINITION_ORPHAN = "definition_orphan"
    RUBRIC = "rubric"
    QUESTION = "question"


class EvidenceDisposition(str, Enum):
    PRESERVED = "preserved"
    MAPPED = "mapped"
    DECISION_REQUIRED = "decision_required"
    PRESERVE_AS_ORPHAN = "preserve_as_orphan"


class IssueSeverity(str, Enum):
    BLOCKER = "blocker"
    WARNING = "warning"


class ArtifactDisposition(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    NO_CHANGE = "no_change"
    REMOVE = "remove"


class InstallDisposition(str, Enum):
    INSTALL = "install"
    ALREADY_INSTALLED = "already_installed"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class DomainReference:
    kind: EvidenceKind
    ref: str

    def __post_init__(self) -> None:
        if not _DOMAIN_REFERENCE.fullmatch(self.ref):
            raise ValueError(f"invalid vertical transition domain reference: {self.ref}")
        if not self.ref.startswith(f"{self.kind.value}:"):
            raise ValueError(
                f"vertical transition reference kind {self.kind.value} does not match {self.ref}"
            )

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "ref": self.ref}


@dataclass(frozen=True)
class VerticalIdentity:
    coordinate: str
    semantic_checksum: str
    artifact_checksum: str = ""
    profile: str = "default"
    modules: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "coordinate": self.coordinate,
            "semantic_checksum": self.semantic_checksum,
            "artifact_checksum": self.artifact_checksum or None,
            "profile": self.profile,
            "modules": list(self.modules),
        }


@dataclass(frozen=True)
class EvidenceCounts:
    definition_fields: int = 0
    assumptions: int = 0
    blockers: int = 0
    definition_orphans: int = 0
    owner_question_evidence: int = 0
    rubric_customizations: int = 0

    @property
    def total(self) -> int:
        return sum(
            (
                self.definition_fields,
                self.assumptions,
                self.blockers,
                self.definition_orphans,
                self.owner_question_evidence,
                self.rubric_customizations,
            )
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "definition_fields": self.definition_fields,
            "assumptions": self.assumptions,
            "blockers": self.blockers,
            "definition_orphans": self.definition_orphans,
            "owner_question_evidence": self.owner_question_evidence,
            "rubric_customizations": self.rubric_customizations,
            "total": self.total,
        }


@dataclass(frozen=True)
class SourceStateImpact:
    evidence: EvidenceCounts

    @property
    def classification(self) -> str:
        return "empty" if self.evidence.total == 0 else "populated"

    @property
    def adoption_eligible(self) -> bool:
        return self.classification == "empty"

    @property
    def migration_required(self) -> bool:
        return not self.adoption_eligible

    def to_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification,
            "adoption_eligible": self.adoption_eligible,
            "migration_required": self.migration_required,
            "evidence": self.evidence.to_dict(),
        }


T = TypeVar("T")


@dataclass(frozen=True)
class BoundedCollection(Generic[T]):
    total: int
    items: tuple[T, ...]
    truncated: bool

    @classmethod
    def build(
        cls,
        items: Iterable[T],
        *,
        key,
        limit: int = VERTICAL_TRANSITION_COLLECTION_LIMIT,
    ) -> "BoundedCollection[T]":
        ordered = tuple(sorted(items, key=key))
        return cls(total=len(ordered), items=ordered[:limit], truncated=len(ordered) > limit)

    @property
    def returned(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "returned": self.returned,
            "truncated": self.truncated,
            "items": [item.to_dict() if hasattr(item, "to_dict") else item for item in self.items],
        }


@dataclass(frozen=True)
class TransitionIssue:
    code: str
    severity: IssueSeverity
    category: str
    reference: str
    recovery_action: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category,
            "reference": self.reference,
            "recovery_action": self.recovery_action,
        }


@dataclass(frozen=True)
class EvidenceTransition:
    source: DomainReference
    disposition: EvidenceDisposition
    target: DomainReference | None = None
    value_present: bool = True
    provenance_present: bool = False
    decision_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source.to_dict(),
            "target": self.target.to_dict() if self.target is not None else None,
            "disposition": self.disposition.value,
            "value_present": self.value_present,
            "provenance_present": self.provenance_present,
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class RequiredDecision:
    decision_id: str
    kind: str
    source: DomainReference
    allowed_actions: tuple[str, ...]
    compatible_target_kinds: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.decision_id,
            "kind": self.kind,
            "source": self.source.to_dict(),
            "allowed_actions": list(self.allowed_actions),
            "compatible_target_kinds": list(self.compatible_target_kinds),
        }


@dataclass(frozen=True)
class StructuralImpact:
    kind: str
    ref: str
    disposition: str
    changed_attributes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "disposition": self.disposition,
            "changed_attributes": list(self.changed_attributes),
        }


@dataclass(frozen=True)
class RubricImpact:
    ref: str
    disposition: str
    target_ref: str | None = None
    decision_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ref": self.ref,
            "disposition": self.disposition,
            "target_ref": self.target_ref,
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class QuestionImpact:
    preserved: BoundedCollection[str]
    revised: BoundedCollection[str]
    created: BoundedCollection[str]
    retired: BoundedCollection[str]
    superseded: BoundedCollection[str]
    inactive_owner_evidence: BoundedCollection[str]
    owner_review_required: BoundedCollection[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "preserved": self.preserved.to_dict(),
            "revised": self.revised.to_dict(),
            "created": self.created.to_dict(),
            "retired": self.retired.to_dict(),
            "superseded": self.superseded.to_dict(),
            "inactive_owner_evidence": self.inactive_owner_evidence.to_dict(),
            "owner_review_required": self.owner_review_required.to_dict(),
        }


@dataclass(frozen=True)
class LockImpact:
    before: VerticalIdentity | None
    after: VerticalIdentity
    dependency_additions: BoundedCollection[dict[str, str]] = field(
        default_factory=lambda: BoundedCollection(total=0, items=(), truncated=False)
    )
    dependency_removals: BoundedCollection[dict[str, str]] = field(
        default_factory=lambda: BoundedCollection(total=0, items=(), truncated=False)
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "before": self.before.to_dict() if self.before is not None else None,
            "after": self.after.to_dict(),
            "dependency_additions": self.dependency_additions.to_dict(),
            "dependency_removals": self.dependency_removals.to_dict(),
        }


@dataclass(frozen=True)
class ArtifactImpact:
    kind: str
    disposition: ArtifactDisposition
    before_semantic_sha256: str | None
    candidate_semantic_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "disposition": self.disposition.value,
            "before_semantic_sha256": self.before_semantic_sha256,
            "candidate_semantic_sha256": self.candidate_semantic_sha256,
        }


@dataclass(frozen=True)
class InstallImpact:
    analysis_fingerprint_sha256: str
    target: VerticalIdentity
    artifact_kinds: BoundedCollection[str]
    dependency_closure: BoundedCollection[dict[str, str]]
    disposition: InstallDisposition
    conflict: bool
    blockers: BoundedCollection[TransitionIssue]
    warnings: BoundedCollection[TransitionIssue]
    operation: TransitionOperation = TransitionOperation.INSTALL
    contract_version: str = VERTICAL_TRANSITION_IMPACT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "operation": self.operation.value,
            "analysis_fingerprint_sha256": self.analysis_fingerprint_sha256,
            "target": self.target.to_dict(),
            "artifact_kinds": self.artifact_kinds.to_dict(),
            "dependency_closure": self.dependency_closure.to_dict(),
            "disposition": self.disposition.value,
            "conflict": self.conflict,
            "blockers": self.blockers.to_dict(),
            "warnings": self.warnings.to_dict(),
        }


@dataclass(frozen=True)
class AdoptionImpact:
    analysis_fingerprint_sha256: str
    source_state: SourceStateImpact
    source: VerticalIdentity | None
    target: VerticalIdentity
    lock: LockImpact
    artifacts: BoundedCollection[ArtifactImpact]
    blockers: BoundedCollection[TransitionIssue]
    warnings: BoundedCollection[TransitionIssue]
    operation: TransitionOperation = TransitionOperation.ADOPT
    contract_version: str = VERTICAL_TRANSITION_IMPACT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "operation": self.operation.value,
            "analysis_fingerprint_sha256": self.analysis_fingerprint_sha256,
            "source_state": self.source_state.to_dict(),
            "source": self.source.to_dict() if self.source is not None else None,
            "target": self.target.to_dict(),
            "lock": self.lock.to_dict(),
            "artifacts": self.artifacts.to_dict(),
            "blockers": self.blockers.to_dict(),
            "warnings": self.warnings.to_dict(),
        }


@dataclass(frozen=True)
class MigrationImpact:
    analysis_fingerprint_sha256: str
    plan_fingerprint_sha256: str | None
    source_state: SourceStateImpact
    source: VerticalIdentity
    target: VerticalIdentity
    sections: BoundedCollection[StructuralImpact]
    evidence_transitions: BoundedCollection[EvidenceTransition]
    rubrics: BoundedCollection[RubricImpact]
    questions: QuestionImpact
    lock: LockImpact
    artifacts: BoundedCollection[ArtifactImpact]
    required_decisions: BoundedCollection[RequiredDecision]
    blockers: BoundedCollection[TransitionIssue]
    warnings: BoundedCollection[TransitionIssue]
    operation: TransitionOperation = TransitionOperation.MIGRATE
    contract_version: str = VERTICAL_TRANSITION_IMPACT_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "operation": self.operation.value,
            "analysis_fingerprint_sha256": self.analysis_fingerprint_sha256,
            "plan_fingerprint_sha256": self.plan_fingerprint_sha256,
            "source_state": self.source_state.to_dict(),
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "sections": self.sections.to_dict(),
            "evidence_transitions": self.evidence_transitions.to_dict(),
            "rubrics": self.rubrics.to_dict(),
            "questions": self.questions.to_dict(),
            "lock": self.lock.to_dict(),
            "artifacts": self.artifacts.to_dict(),
            "required_decisions": self.required_decisions.to_dict(),
            "blockers": self.blockers.to_dict(),
            "warnings": self.warnings.to_dict(),
        }


VerticalTransitionImpact = InstallImpact | AdoptionImpact | MigrationImpact


def bounded_strings(values: Iterable[str]) -> BoundedCollection[str]:
    return BoundedCollection.build(values, key=lambda item: item)


def impact_fingerprint(payload: dict[str, object]) -> str:
    normalized = dict(payload)
    normalized.pop("analysis_fingerprint_sha256", None)
    normalized.pop("plan_fingerprint_sha256", None)
    return semantic_sha256(normalized)
