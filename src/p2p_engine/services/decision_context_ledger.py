from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from p2p_engine.core.decision_context import (
    Activation,
    Authority,
    Canonicality,
    Confidence,
    DecisionContextDiagnostic,
    DecisionContextEvidence,
    DecisionContextNode,
    DecisionContextRecord,
    DecisionContextRelation,
    DiagnosticSeverity,
    NodeType,
    RecordKind,
    RelationType,
    SourceDocument,
    SourceKind,
)
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionEffectiveState,
    ProposalDecisionEvent,
    ProposalDecisionEventType,
    ProposalDecisionLedger,
    ProposalDecisionLifecycleView,
    ProposalDecisionLineageKind,
)
from p2p_engine.services.lifecycle_authority import lifecycle_from_ledger
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    render_decision_projection,
)


@dataclass(frozen=True)
class ExtractedLedgerContext:
    ledger: ProposalDecisionLedger | None
    lifecycle: ProposalDecisionLifecycleView | None
    records: tuple[DecisionContextRecord, ...]
    evidence: tuple[DecisionContextEvidence, ...]
    nodes: tuple[DecisionContextNode, ...]
    relations: tuple[DecisionContextRelation, ...]
    diagnostics: tuple[DecisionContextDiagnostic, ...]


class DecisionContextLedgerExtractor:
    def __init__(self, codec: ProposalDecisionLedgerCodec | None = None) -> None:
        self.codec = codec or ProposalDecisionLedgerCodec()

    def extract(
        self,
        ledger_document: SourceDocument,
        *,
        decision_projection: SourceDocument | None,
        related_record_ids: Sequence[str],
    ) -> ExtractedLedgerContext:
        try:
            ledger = self.codec.loads_mapping(
                _thaw(ledger_document.frontmatter),
                expected_proposal_id=ledger_document.owner_id,
            )
        except ValueError as exc:
            return ExtractedLedgerContext(
                ledger=None,
                lifecycle=None,
                records=(),
                evidence=(),
                nodes=(),
                relations=(),
                diagnostics=(
                    _diagnostic(
                        code="DC-AUTHORITY-INVALID-DECISION-LEDGER",
                        severity=DiagnosticSeverity.ERROR,
                        message=str(exc),
                        source_path=ledger_document.path,
                        target_id=ledger_document.owner_id,
                        recovery="Repair the ledger through the governed decision repair workflow.",
                    ),
                ),
            )

        lifecycle = lifecycle_from_ledger(ledger)
        intervals_by_event = _intervals_by_event(lifecycle)
        records: list[DecisionContextRecord] = []
        evidence: list[DecisionContextEvidence] = []
        nodes: list[DecisionContextNode] = [
            DecisionContextNode(
                node_id=f"decision:{ledger.proposal_id}",
                node_type=NodeType.DECISION,
                label=f"Decision for {ledger.proposal_id}",
            )
        ]
        relations: list[DecisionContextRelation] = []
        for index, event in enumerate(ledger.events):
            authority, activation = _event_authority(event, lifecycle)
            item_evidence = _event_evidence(
                ledger_document,
                event,
                index,
                authority=authority,
                activation=activation,
            )
            evidence.append(item_evidence)
            interval = intervals_by_event.get(event.event_id, MappingProxyType({}))
            common = {
                "owner_id": ledger.proposal_id,
                "source_kind": ledger_document.source_kind,
                "activation": activation,
                "authority": authority,
                "evidence_ids": (item_evidence.evidence_id,),
                "related_record_ids": tuple(related_record_ids),
                "canonical_date": event.decided_on,
                "event_id": event.event_id,
                "head_event_id": ledger.head_event_id or "",
                "decision_semantic_sha256": event.decision_semantic_sha256,
                "authority_interval": interval,
                "lineage": MappingProxyType(event.lineage.to_dict()),
            }
            records.append(
                _record(
                    kind=RecordKind.EVENT,
                    suffix="event",
                    text=event.event_type.value,
                    **common,
                )
            )
            records.append(
                _record(
                    kind=RecordKind.DECISION_STATE,
                    suffix="state",
                    text=event.effective_state.value,
                    **common,
                )
            )
            records.append(
                _record(
                    kind=(
                        RecordKind.DECISION_QUALIFIER
                        if event.event_type
                        == ProposalDecisionEventType.accepted_with_changes
                        else RecordKind.DECISION_REASON
                    ),
                    suffix="reason",
                    text=event.rationale,
                    **common,
                )
            )
            for condition_index, condition in enumerate(event.conditions):
                records.append(
                    _record(
                        kind=RecordKind.DECISION_QUALIFIER,
                        suffix=f"condition:{condition.condition_id}:{condition_index}",
                        text=condition.text,
                        **common,
                    )
                )

            event_node_id = f"decision-event:{event.event_id}"
            nodes.append(
                DecisionContextNode(
                    node_id=event_node_id,
                    node_type=NodeType.DECISION_EVENT,
                    label=f"{event.event_type.value} {event.decided_on}",
                    existence=(
                        "current"
                        if event.event_id == ledger.head_event_id
                        else "historical"
                    ),
                )
            )
            relations.append(
                _relation(
                    source_id=event_node_id,
                    source_type=NodeType.DECISION_EVENT,
                    target_id=f"decision:{ledger.proposal_id}",
                    target_type=NodeType.DECISION,
                    relation_type=RelationType.AFFECTS_DECISION,
                    event=event,
                    authority=authority,
                    activation=activation,
                    evidence_id=item_evidence.evidence_id,
                )
            )
            if event.predecessor.event_id:
                relations.append(
                    _relation(
                        source_id=f"decision-event:{event.predecessor.event_id}",
                        source_type=NodeType.DECISION_EVENT,
                        target_id=event_node_id,
                        target_type=NodeType.DECISION_EVENT,
                        relation_type=RelationType.PRECEDES,
                        event=event,
                        authority=authority,
                        activation=activation,
                        evidence_id=item_evidence.evidence_id,
                    )
                )
            if event.affected_decision.event_id:
                relations.append(
                    _relation(
                        source_id=event_node_id,
                        source_type=NodeType.DECISION_EVENT,
                        target_id=f"decision-event:{event.affected_decision.event_id}",
                        target_type=NodeType.DECISION_EVENT,
                        relation_type=(
                            RelationType.REINSTATES
                            if event.event_type == ProposalDecisionEventType.reinstated
                            else RelationType.AFFECTS_DECISION
                        ),
                        event=event,
                        authority=authority,
                        activation=activation,
                        evidence_id=item_evidence.evidence_id,
                    )
                )
            relations.extend(
                _lineage_relations(
                    event,
                    event_node_id=event_node_id,
                    evidence_id=item_evidence.evidence_id,
                    authority=authority,
                    activation=activation,
                )
            )

        diagnostics = list(
            _projection_diagnostics(
                ledger,
                decision_projection=decision_projection,
            )
        )
        return ExtractedLedgerContext(
            ledger=ledger,
            lifecycle=lifecycle,
            records=tuple(records),
            evidence=tuple(evidence),
            nodes=tuple(nodes),
            relations=tuple(relations),
            diagnostics=tuple(diagnostics),
        )


def proposal_authority(
    lifecycle: ProposalDecisionLifecycleView,
) -> tuple[Authority, Activation]:
    if lifecycle.active:
        return Authority.ACCEPTED_PROPOSAL_CONTEXT, Activation.ACTIVE
    if lifecycle.effective_state == ProposalDecisionEffectiveState.undecided:
        return Authority.DRAFT_PROPOSAL, Activation.EXPLORATORY
    if lifecycle.effective_state == ProposalDecisionEffectiveState.deferred:
        return Authority.HISTORICAL_PROPOSAL, Activation.UNRESOLVED
    if lifecycle.effective_state == ProposalDecisionEffectiveState.unknown_legacy:
        return Authority.UNKNOWN, Activation.UNRESOLVED
    return Authority.HISTORICAL_PROPOSAL, Activation.HISTORICAL


def _event_authority(
    event: ProposalDecisionEvent,
    lifecycle: ProposalDecisionLifecycleView,
) -> tuple[Authority, Activation]:
    active_event_ids = {
        interval.active_event_id
        for interval in lifecycle.intervals
        if interval.active
    }
    if lifecycle.active and (
        event.event_id in active_event_ids or event.event_id == lifecycle.head_event_id
    ):
        authority = (
            Authority.CONDITIONALLY_ACCEPTED_DECISION
            if lifecycle.effective_state
            == ProposalDecisionEffectiveState.accepted_with_changes
            else Authority.ACCEPTED_DECISION
        )
        return authority, Activation.ACTIVE
    if event.event_type == ProposalDecisionEventType.deferred:
        return Authority.HISTORICAL_PROPOSAL, Activation.UNRESOLVED
    return Authority.HISTORICAL_PROPOSAL, Activation.HISTORICAL


def _intervals_by_event(
    lifecycle: ProposalDecisionLifecycleView,
) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for interval in lifecycle.intervals:
        frozen = MappingProxyType(interval.to_dict())
        result[interval.opened_by_event_id] = frozen
        result.setdefault(interval.active_event_id, frozen)
        if interval.closed_by_event_id:
            result[interval.closed_by_event_id] = frozen
    return result


def _event_evidence(
    document: SourceDocument,
    event: ProposalDecisionEvent,
    index: int,
    *,
    authority: Authority,
    activation: Activation,
) -> DecisionContextEvidence:
    fragment_id = f"yaml:/proposal_decision_ledger/events/{index}"
    return DecisionContextEvidence(
        evidence_id=_stable_id(
            "dce",
            document.owner_id,
            document.source_kind.value,
            event.event_id,
        ),
        source_path=document.path,
        source_sha256=document.sha256 or "",
        source_kind=document.source_kind,
        fragment_id=fragment_id,
        fragment_label=event.event_type.value,
        span=None,
        canonicality=Canonicality.CANONICAL,
        authority=authority,
        activation=activation,
        confidence=Confidence.EXPLICIT,
        completeness=document.completeness,
    )


def _record(
    *,
    owner_id: str,
    source_kind: SourceKind,
    kind: RecordKind,
    suffix: str,
    activation: Activation,
    authority: Authority,
    text: str,
    evidence_ids: tuple[str, ...],
    related_record_ids: tuple[str, ...],
    canonical_date: str,
    event_id: str,
    head_event_id: str,
    decision_semantic_sha256: str,
    authority_interval: Mapping[str, object],
    lineage: Mapping[str, object],
) -> DecisionContextRecord:
    return DecisionContextRecord(
        record_id=_stable_id("dcr", owner_id, event_id, suffix),
        kind=kind,
        owner_type=NodeType.PROPOSAL,
        owner_id=owner_id,
        activation=activation,
        authority=authority,
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        evidence_ids=evidence_ids,
        related_record_ids=related_record_ids,
        canonical_date=canonical_date,
        event_id=event_id,
        head_event_id=head_event_id,
        decision_semantic_sha256=decision_semantic_sha256,
        authority_interval=authority_interval,
        lineage=lineage,
    )


def _relation(
    *,
    source_id: str,
    source_type: NodeType,
    target_id: str,
    target_type: NodeType,
    relation_type: RelationType,
    event: ProposalDecisionEvent,
    authority: Authority,
    activation: Activation,
    evidence_id: str,
) -> DecisionContextRelation:
    return DecisionContextRelation(
        relation_id=_stable_id(
            "dcrl",
            source_id,
            relation_type.value,
            target_id,
            event.event_id,
        ),
        source_id=source_id,
        source_type=source_type,
        target_id=target_id,
        target_type=target_type,
        relation_type=relation_type,
        scope="proposal_decision_lifecycle",
        activation=activation,
        authority=authority,
        confidence=Confidence.EXPLICIT,
        evidence_ids=(evidence_id,),
    )


def _lineage_relations(
    event: ProposalDecisionEvent,
    *,
    event_node_id: str,
    evidence_id: str,
    authority: Authority,
    activation: Activation,
) -> tuple[DecisionContextRelation, ...]:
    relation_type = {
        ProposalDecisionLineageKind.supersedes: RelationType.SUPERSEDES,
        ProposalDecisionLineageKind.split: RelationType.SPLIT_INTO,
        ProposalDecisionLineageKind.merged_into: RelationType.MERGED_INTO,
    }.get(event.lineage.kind)
    if relation_type is None:
        return ()
    return tuple(
        _relation(
            source_id=event_node_id,
            source_type=NodeType.DECISION_EVENT,
            target_id=target,
            target_type=NodeType.PROPOSAL,
            relation_type=relation_type,
            event=event,
            authority=authority,
            activation=activation,
            evidence_id=evidence_id,
        )
        for target in event.lineage.targets
    )


def _projection_diagnostics(
    ledger: ProposalDecisionLedger,
    *,
    decision_projection: SourceDocument | None,
) -> tuple[DecisionContextDiagnostic, ...]:
    if decision_projection is None or decision_projection._content is None:
        return ()
    try:
        actual = decision_projection._content.decode("utf-8")
    except UnicodeDecodeError:
        return ()
    expected = render_decision_projection(
        ledger.proposal_id,
        ledger.events[-1] if ledger.events else None,
        empty_state=ledger.effective_state,
    )
    if actual == expected:
        return ()
    return (
        _diagnostic(
            code="DC-AUTHORITY-PROJECTION-DIVERGENCE",
            severity=DiagnosticSeverity.WARNING,
            message=(
                "decision.md differs from the ledger-derived projection and "
                "does not contribute decision authority."
            ),
            source_path=decision_projection.path,
            target_id=ledger.proposal_id,
            recovery="Preview and apply the governed projection repair.",
        ),
    )


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _diagnostic(
    *,
    code: str,
    severity: DiagnosticSeverity,
    message: str,
    source_path: str,
    target_id: str,
    recovery: str,
) -> DecisionContextDiagnostic:
    identity = "|".join((code, source_path, target_id, message))
    return DecisionContextDiagnostic(
        diagnostic_id=f"dcd:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}",
        code=code,
        severity=severity,
        fatal=False,
        message=message,
        source_path=source_path,
        target_id=target_id,
        recovery=recovery,
    )


def _stable_id(prefix: str, *parts: str) -> str:
    identity = "|".join(parts)
    return f"{prefix}:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"
