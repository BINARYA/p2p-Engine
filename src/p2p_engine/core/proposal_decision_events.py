from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

from p2p_engine.core.mutation_preview import MutationPreview, MutationResult


PROPOSAL_DECISION_IMPACT_POLICY_VERSION = 1
PROPOSAL_DECISION_DEPENDENCY_VOCABULARY_VERSION = 1
PROPOSAL_DECISION_REMEDIATION_VOCABULARY_VERSION = 1


class ProposalDecisionEventType(StrEnum):
    accepted = "accepted"
    accepted_with_changes = "accepted_with_changes"
    deferred = "deferred"
    withdrawn = "withdrawn"
    rejected = "rejected"
    revoked = "revoked"
    superseded = "superseded"
    split = "split"
    merged_into_other = "merged_into_other"
    reinstated = "reinstated"


class ProposalDecisionEffectiveState(StrEnum):
    undecided = "undecided"
    accepted = "accepted"
    accepted_with_changes = "accepted_with_changes"
    deferred = "deferred"
    withdrawn = "withdrawn"
    rejected = "rejected"
    revoked = "revoked"
    superseded = "superseded"
    split = "split"
    merged_into_other = "merged_into_other"


class ProposalDecisionAuthorityResolution(StrEnum):
    resolved = "resolved"
    invalid = "invalid"


class ProposalDecisionLineageKind(StrEnum):
    supersedes = "supersedes"
    split = "split"
    merged_into = "merged_into"


class ProposalDecisionBindingStatus(StrEnum):
    current = "current"
    diverged = "diverged"
    unavailable = "unavailable"


class ProposalDecisionDependencyKind(StrEnum):
    change = "change"
    work = "work"
    software_spec = "software_spec"
    vertical_evidence = "vertical_evidence"
    project_projection = "project_projection"
    decision_context = "decision_context"
    relation = "relation"
    conflict = "conflict"
    freshness = "freshness"
    publication = "publication"


class ProposalDecisionDependencyStatus(StrEnum):
    active = "active"
    completed = "completed"
    terminal = "terminal"
    historical = "historical"
    generated = "generated"
    current = "current"
    stale = "stale"
    unknown = "unknown"


class ProposalDecisionImpactSeverity(StrEnum):
    blocker = "blocker"
    high = "high"
    medium = "medium"
    low = "low"
    informational = "informational"


class ProposalDecisionImpactCompleteness(StrEnum):
    complete = "complete"
    incomplete = "incomplete"


class ProposalDecisionDependencyControl(StrEnum):
    generated = "generated"
    curated = "curated"
    owner_controlled = "owner_controlled"


@dataclass(frozen=True)
class ProposalDecisionCondition:
    condition_id: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.condition_id, "text": self.text}


@dataclass(frozen=True)
class ProposalDecisionAuthorityEvidence:
    owner_id: str
    owner_role: str
    executor_actor_id: str
    executor_kind: str
    channel: str
    permission_policy_sha256: str
    consent_id: str | None = None
    consent_sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "owner_id": self.owner_id,
            "owner_role": self.owner_role,
            "executor_actor_id": self.executor_actor_id,
            "executor_kind": self.executor_kind,
            "channel": self.channel,
            "permission_policy_sha256": self.permission_policy_sha256,
            "consent_id": self.consent_id,
            "consent_sha256": self.consent_sha256,
        }


@dataclass(frozen=True)
class ProposalDecisionPredecessor:
    event_id: str | None = None
    event_sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"event_id": self.event_id, "event_sha256": self.event_sha256}


@dataclass(frozen=True)
class ProposalDecisionAffectedDecision:
    event_id: str | None = None
    decision_semantic_sha256: str | None = None
    revocation_event_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "decision_semantic_sha256": self.decision_semantic_sha256,
            "revocation_event_id": self.revocation_event_id,
        }


@dataclass(frozen=True)
class ProposalDecisionLineage:
    kind: ProposalDecisionLineageKind | None = None
    targets: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value if self.kind is not None else None,
            "targets": list(self.targets),
        }


@dataclass(frozen=True)
class ProposalDecisionImpactBinding:
    required: bool = False
    preview_token: str | None = None
    source_fingerprint_sha256: str | None = None
    total_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "required": self.required,
            "preview_token": self.preview_token,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "total_count": self.total_count,
        }


@dataclass(frozen=True)
class ProposalDecisionImpactItem:
    impact_id: str
    dependency_kind: ProposalDecisionDependencyKind
    dependency_id: str
    dependency_status: ProposalDecisionDependencyStatus
    dependency_control: ProposalDecisionDependencyControl
    relationship: str
    authority_effect: str
    source_paths: tuple[str, ...]
    source_fingerprint_sha256: str
    remediation_kind: str
    remediation_command: str
    severity: ProposalDecisionImpactSeverity

    def to_dict(self) -> dict[str, object]:
        return {
            "impact_id": self.impact_id,
            "dependency_kind": self.dependency_kind.value,
            "dependency_id": self.dependency_id,
            "dependency_status": self.dependency_status.value,
            "dependency_control": self.dependency_control.value,
            "relationship": self.relationship,
            "authority_effect": self.authority_effect,
            "source_paths": list(self.source_paths),
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "remediation_kind": self.remediation_kind,
            "remediation_command": self.remediation_command,
            "severity": self.severity.value,
        }


@dataclass(frozen=True)
class ProposalDecisionImpactSnapshot:
    proposal_id: str
    source_head_event_id: str | None
    event_type: ProposalDecisionEventType
    completeness: ProposalDecisionImpactCompleteness
    items: tuple[ProposalDecisionImpactItem, ...]
    source_fingerprint_sha256: str
    preview_token: str
    source_bytes: Mapping[str, bytes | None] = field(default_factory=dict, repr=False)
    kind_counts: Mapping[str, int] = field(default_factory=dict)
    status_counts: Mapping[str, int] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()
    access_counters: Mapping[str, int] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.completeness == ProposalDecisionImpactCompleteness.complete

    @property
    def total_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "source_head_event_id": self.source_head_event_id,
            "event_type": self.event_type.value,
            "completeness": self.completeness.value,
            "complete": self.complete,
            "items": [item.to_dict() for item in self.items],
            "total_count": self.total_count,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "preview_token": self.preview_token,
            "kind_counts": dict(self.kind_counts),
            "status_counts": dict(self.status_counts),
            "diagnostics": list(self.diagnostics),
            "access_counters": dict(self.access_counters),
        }

    def provider_payload(self) -> dict[str, object]:
        return {
            **self.to_dict(),
            "source_bytes": dict(self.source_bytes),
        }


@dataclass(frozen=True)
class ProposalDecisionImpactPage:
    proposal_id: str
    source_head_event_id: str | None
    items: tuple[ProposalDecisionImpactItem, ...]
    total_count: int
    returned_count: int
    omitted_count: int
    next_cursor: str | None
    completeness: ProposalDecisionImpactCompleteness
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "source_head_event_id": self.source_head_event_id,
            "items": [item.to_dict() for item in self.items],
            "total_count": self.total_count,
            "returned_count": self.returned_count,
            "omitted_count": self.omitted_count,
            "next_cursor": self.next_cursor,
            "completeness": self.completeness.value,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class ProposalDecisionReadinessBinding:
    source_fingerprint_sha256: str | None = None
    owner_override: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "owner_override": self.owner_override,
        }


@dataclass(frozen=True)
class ProposalDecisionMutationBinding:
    preview_token: str
    request_fingerprint_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "preview_token": self.preview_token,
            "request_fingerprint_sha256": self.request_fingerprint_sha256,
        }


@dataclass(frozen=True)
class ProposalDecisionEvent:
    event_schema_version: int
    event_id: str
    operation_key: str
    proposal_id: str
    event_type: ProposalDecisionEventType
    effective_state: ProposalDecisionEffectiveState
    rationale: str
    conditions: tuple[ProposalDecisionCondition, ...]
    decided_on: str
    authority: ProposalDecisionAuthorityEvidence
    predecessor: ProposalDecisionPredecessor
    proposal_semantic_sha256: str
    decision_semantic_sha256: str
    affected_decision: ProposalDecisionAffectedDecision
    lineage: ProposalDecisionLineage
    impact: ProposalDecisionImpactBinding
    readiness: ProposalDecisionReadinessBinding
    mutation: ProposalDecisionMutationBinding
    event_sha256: str

    def to_dict(self, *, include_hash: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "event_schema_version": self.event_schema_version,
            "event_id": self.event_id,
            "operation_key": self.operation_key,
            "proposal_id": self.proposal_id,
            "event_type": self.event_type.value,
            "effective_state": self.effective_state.value,
            "rationale": self.rationale,
            "conditions": [item.to_dict() for item in self.conditions],
            "decided_on": self.decided_on,
            "authority": self.authority.to_dict(),
            "predecessor": self.predecessor.to_dict(),
            "proposal_semantic_sha256": self.proposal_semantic_sha256,
            "decision_semantic_sha256": self.decision_semantic_sha256,
            "affected_decision": self.affected_decision.to_dict(),
            "lineage": self.lineage.to_dict(),
            "impact": self.impact.to_dict(),
            "readiness": self.readiness.to_dict(),
            "mutation": self.mutation.to_dict(),
        }
        if include_hash:
            payload["event_sha256"] = self.event_sha256
        return payload


@dataclass(frozen=True)
class ProposalDecisionLedger:
    contract_version: int
    proposal_id: str
    authority_resolution: ProposalDecisionAuthorityResolution
    effective_state: ProposalDecisionEffectiveState
    head_event_id: str | None
    events: tuple[ProposalDecisionEvent, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_decision_ledger": {
                "contract_version": self.contract_version,
                "proposal_id": self.proposal_id,
                "authority_resolution": self.authority_resolution.value,
                "effective_state": self.effective_state.value,
                "head_event_id": self.head_event_id,
                "events": [event.to_dict() for event in self.events],
            }
        }


@dataclass(frozen=True)
class ProposalDecisionAuthorityInterval:
    opened_by_event_id: str
    active_event_id: str
    decision_semantic_sha256: str
    effective_state: ProposalDecisionEffectiveState
    opened_on: str
    closed_by_event_id: str | None = None
    closed_on: str | None = None
    precision: str = "event_date"

    @property
    def active(self) -> bool:
        return self.closed_by_event_id is None

    def to_dict(self) -> dict[str, object]:
        return {
            "opened_by_event_id": self.opened_by_event_id,
            "active_event_id": self.active_event_id,
            "decision_semantic_sha256": self.decision_semantic_sha256,
            "effective_state": self.effective_state.value,
            "opened_on": self.opened_on,
            "closed_by_event_id": self.closed_by_event_id,
            "closed_on": self.closed_on,
            "precision": self.precision,
            "active": self.active,
        }


@dataclass(frozen=True)
class ProposalDecisionLifecycleView:
    proposal_id: str
    source_model: str
    authority_resolution: ProposalDecisionAuthorityResolution
    effective_state: ProposalDecisionEffectiveState
    head_event_type: ProposalDecisionEventType | None
    head_event_id: str | None
    event_count: int
    committed: bool
    active: bool
    ever_active: bool
    decision_semantic_sha256: str | None
    proposal_semantic_sha256: str | None
    proposal_binding_status: ProposalDecisionBindingStatus
    intervals: tuple[ProposalDecisionAuthorityInterval, ...] = ()
    lineage: ProposalDecisionLineage = ProposalDecisionLineage()
    diagnostics: tuple[str, ...] = ()
    current_event: ProposalDecisionEvent | None = None
    suggested_next_command: str | None = None

    @property
    def active_projection(self) -> bool:
        return self.active and self.proposal_binding_status == ProposalDecisionBindingStatus.current

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "source_model": self.source_model,
            "authority_resolution": self.authority_resolution.value,
            "effective_state": self.effective_state.value,
            "head_event_type": self.head_event_type.value if self.head_event_type else None,
            "head_event_id": self.head_event_id,
            "event_count": self.event_count,
            "committed": self.committed,
            "active": self.active,
            "active_projection": self.active_projection,
            "ever_active": self.ever_active,
            "decision_semantic_sha256": self.decision_semantic_sha256,
            "proposal_semantic_sha256": self.proposal_semantic_sha256,
            "proposal_binding_status": self.proposal_binding_status.value,
            "intervals": [item.to_dict() for item in self.intervals],
            "lineage": self.lineage.to_dict(),
            "diagnostics": list(self.diagnostics),
            "suggested_next_command": self.suggested_next_command,
        }


@dataclass(frozen=True)
class ProposalDecisionRequest:
    proposal_id: str
    event_type: ProposalDecisionEventType
    reason: str
    actor_id: str
    executor_actor_id: str
    executor_kind: str = "person"
    channel: str = "cli"
    decided_on: str = ""
    operation_key: str = ""
    source_head_event_id: str | None = None
    conditions: tuple[ProposalDecisionCondition, ...] = ()
    lineage: ProposalDecisionLineage = ProposalDecisionLineage()
    affected_event_id: str | None = None
    revocation_event_id: str | None = None
    impact_preview_token: str | None = None
    drift_acknowledged: bool = False
    readiness_override: bool = False
    consent_id: str | None = None
    consent_sha256: str | None = None


@dataclass(frozen=True)
class ProposalDecisionPreview:
    request: ProposalDecisionRequest
    mutation: MutationPreview
    event: ProposalDecisionEvent
    ledger: ProposalDecisionLedger
    lifecycle: ProposalDecisionLifecycleView
    impact: Mapping[str, object] = field(default_factory=dict)
    candidate_bytes: Mapping[str, bytes] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "request": {
                "proposal_id": self.request.proposal_id,
                "event_type": self.request.event_type.value,
                "reason": self.request.reason,
                "actor_id": self.request.actor_id,
                "executor_actor_id": self.request.executor_actor_id,
                "decided_on": self.request.decided_on,
                "operation_key": self.request.operation_key,
                "source_head_event_id": self.request.source_head_event_id,
                "conditions": [
                    item.to_dict() for item in self.request.conditions
                ],
                "lineage": self.request.lineage.to_dict(),
                "affected_event_id": self.request.affected_event_id,
                "revocation_event_id": self.request.revocation_event_id,
                "drift_acknowledged": self.request.drift_acknowledged,
                "readiness_override": self.request.readiness_override,
            },
            "preview": self.mutation.to_dict(),
            "event": self.event.to_dict(),
            "lifecycle": self.lifecycle.to_dict(),
            "impact": dict(self.impact),
        }


@dataclass(frozen=True)
class ProposalDecisionApplyResult:
    status: str
    event: ProposalDecisionEvent
    lifecycle: ProposalDecisionLifecycleView
    mutation: MutationResult | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "event": self.event.to_dict(),
            "lifecycle": self.lifecycle.to_dict(),
            "mutation": self.mutation.to_dict() if self.mutation is not None else None,
        }


@dataclass(frozen=True)
class ProposalDecisionHistoryPage:
    proposal_id: str
    head_event_id: str | None
    items: tuple[ProposalDecisionEvent, ...]
    total_count: int
    returned_count: int
    next_cursor: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "head_event_id": self.head_event_id,
            "items": [item.to_dict() for item in self.items],
            "total_count": self.total_count,
            "returned_count": self.returned_count,
            "next_cursor": self.next_cursor,
        }
