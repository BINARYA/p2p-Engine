from __future__ import annotations

import json
from pathlib import Path

import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.decision_context import (
    Activation,
    Authority,
    ContextBudget,
    RecordKind,
    RelationType,
    RetrievalRequest,
    SourceClassification,
    SourceKind,
    to_json_ready,
)
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionEventType,
)
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.services.decision_context_retrieval import (
    DecisionContextRetrievalService,
)
from p2p_engine.services.decision_context_sources import FileSourceAccessor
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    render_decision_projection,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import (
    append_event,
    ledger_with_acceptance,
    write_current_proposal,
    ensure_global_scope,
)


class _ReverseAccessor(FileSourceAccessor):
    def proposal_directories(self, proposals_root: Path) -> list[Path]:
        return list(reversed(super().proposal_directories(proposals_root)))


def _apply_record(
    workspace: P2PWorkspace,
    proposal_id: str,
    outcome: DecisionOutcome,
    reason: str,
):
    ensure_global_scope(workspace, proposal_id)
    preview = workspace.record_decision(
        proposal_id,
        outcome,
        reason,
        "owner",
    )
    return workspace.apply_proposal_decision(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )


def _workspace_with_reinstatement(
    root: Path,
) -> tuple[P2PWorkspace, str, object, object, object]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Ledger decision context", owner="owner")
    proposal = workspace.create_proposal_with_details(
        "Ledger context",
        problem="Decision authority must remain explainable.",
        proposal="Index every governed decision event.",
    )
    accepted = _apply_record(
        workspace,
        proposal.proposal_id,
        DecisionOutcome.accepted,
        "Adopt the ledger context.",
    )
    service = workspace._proposal_decision_service()
    revoked_preview = service.preview(
        service.request(
            proposal_id=proposal.proposal_id,
            event_type=ProposalDecisionEventType.revoked,
            reason="The accepted direction is invalid.",
            actor_id="owner",
        )
    )
    revoked = service.apply(
        revoked_preview.request,
        preview_token=revoked_preview.mutation.preview_token,
        confirm=True,
    )
    reinstated_preview = service.preview(
        service.request(
            proposal_id=proposal.proposal_id,
            event_type=ProposalDecisionEventType.reinstated,
            reason="The original direction is valid again.",
            actor_id="owner",
            affected_event_id=accepted.event.event_id,
            revocation_event_id=revoked.event.event_id,
        )
    )
    reinstated = service.apply(
        reinstated_preview.request,
        preview_token=reinstated_preview.mutation.preview_token,
        confirm=True,
    )
    return workspace, proposal.proposal_id, accepted, revoked, reinstated


def test_v3_catalog_uses_ledger_as_canonical_and_projection_as_derived(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, *_ = _workspace_with_reinstatement(tmp_path)

    index = workspace.decision_context_index()
    proposal_sources = {
        item.source_kind: item
        for item in index.sources
        if item.owner_id == proposal_id
    }

    assert index.source_catalog_version == "decision-context-sources-v4"
    assert (
        proposal_sources[SourceKind.PROPOSAL_DECISION_LEDGER].classification
        == SourceClassification.CANONICAL_SEMANTIC
    )
    assert (
        proposal_sources[SourceKind.PROPOSAL_DECISION].classification
        == SourceClassification.DERIVED_PROJECTION
    )
    assert all(count == 1 for count in index.access_stats.reads.values())
    assert all(count == 1 for count in index.access_stats.hashes.values())
    assert all(count == 1 for count in index.access_stats.parses.values())


def test_v3_extracts_event_authority_intervals_and_lineage_relations(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, accepted, revoked, reinstated = (
        _workspace_with_reinstatement(tmp_path)
    )

    index = workspace.decision_context_index()
    events = [
        item
        for item in index.records
        if item.owner_id == proposal_id
        and item.kind == RecordKind.EVENT
        and item.event_id
    ]
    events_by_id = {item.event_id: item for item in events}

    assert [
        events_by_id[item.event.event_id].text
        for item in (accepted, revoked, reinstated)
    ] == [
        "accepted",
        "revoked",
        "reinstated",
    ]
    assert events_by_id[accepted.event.event_id].activation == Activation.ACTIVE
    assert events_by_id[accepted.event.event_id].authority == (
        Authority.ACCEPTED_DECISION
    )
    assert events_by_id[revoked.event.event_id].activation == (
        Activation.HISTORICAL
    )
    assert events_by_id[reinstated.event.event_id].activation == Activation.ACTIVE
    assert all(item.head_event_id == reinstated.event.event_id for item in events)
    assert events_by_id[accepted.event.event_id].authority_interval[
        "closed_by_event_id"
    ] == (
        revoked.event.event_id
    )
    assert events_by_id[reinstated.event.event_id].authority_interval[
        "active_event_id"
    ] == (
        accepted.event.event_id
    )
    relation_types = [item.relation_type for item in index.relations]
    assert relation_types.count(RelationType.PRECEDES) == 2
    assert RelationType.REINSTATES in relation_types
    assert len(
        [
            item
            for item in index.nodes
            if item.node_type.value == "decision_event"
        ]
    ) == 3


def test_projection_edit_only_reports_drift_and_keeps_semantic_fingerprint(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Projection context", owner="owner")
    proposal = workspace.create_proposal("Projection context")
    _apply_record(
        workspace,
        proposal.proposal_id,
        DecisionOutcome.accepted,
        "Use the canonical ledger.",
    )
    first = workspace.decision_context_index()
    decision_path = tmp_path / proposal.path / "decision.md"
    decision_path.write_text("manually changed projection\n", encoding="utf-8")

    second = workspace.decision_context_index()

    assert first.source_fingerprint_sha256 != second.source_fingerprint_sha256
    assert first.semantic_fingerprint_sha256 == second.semantic_fingerprint_sha256
    assert len(
        [
            item
            for item in second.records
            if item.owner_id == proposal.proposal_id
            and item.kind == RecordKind.DECISION_STATE
        ]
    ) == 1
    assert any(
        item.code == "DC-AUTHORITY-PROJECTION-DIVERGENCE"
        for item in second.diagnostics
    )


def test_v3_multi_event_scale_is_deterministic_and_bounded(tmp_path: Path) -> None:
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(
        yaml.safe_dump(
            {"workspace_schema": {"current_version": 4}},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    codec = ProposalDecisionLedgerCodec()
    for number in range(1, 101):
        proposal_id = f"PROP-{number:03d}"
        ledger, accepted = ledger_with_acceptance(proposal_id)
        if number % 2 == 0:
            ledger, _ = append_event(
                ledger,
                event_type=ProposalDecisionEventType.revoked,
                affected=accepted,
                reason=f"Revoke scale decision {number}.",
            )
        proposal_dir = (
            tmp_path
            / ".p2p"
            / "proposals"
            / f"{proposal_id.lower()}-scale"
        )
        write_current_proposal(proposal_dir, ledger)
        (proposal_dir / "decision.md").write_text(
            render_decision_projection(
                proposal_id,
                ledger.events[-1],
                empty_state=ledger.effective_state,
            ),
            encoding="utf-8",
        )

    normal = ProjectDecisionContextService(root=tmp_path).build_index()
    reversed_index = ProjectDecisionContextService(
        root=tmp_path,
        source_accessor=_ReverseAccessor(),
    ).build_index()
    packet = DecisionContextRetrievalService().retrieve(
        normal,
        RetrievalRequest(
            ContextBudget.MEDIUM,
            idea_text="append only ledger decisions",
        ),
    )

    assert normal.source_fingerprint_sha256 == (
        reversed_index.source_fingerprint_sha256
    )
    assert normal.semantic_fingerprint_sha256 == (
        reversed_index.semantic_fingerprint_sha256
    )
    assert len(
        [item for item in normal.records if item.kind == RecordKind.EVENT]
    ) == 150
    assert all(count == 1 for count in normal.access_stats.reads.values())
    assert all(count == 1 for count in normal.access_stats.parses.values())
    assert len(json.dumps(to_json_ready(packet))) <= 40_000
