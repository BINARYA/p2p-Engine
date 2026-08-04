from __future__ import annotations

import pytest

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAuthorityResolution,
    ProposalDecisionBindingStatus,
    ProposalDecisionEffectiveState,
    ProposalDecisionEventType,
)
from p2p_engine.services.lifecycle_authority import (
    decision_reconsideration_command,
    effective_state_for_event,
    lifecycle_from_ledger,
    require_transition,
    transition_allowed,
)
from tests.proposal_decision_fixtures import append_event, ledger_with_acceptance
from tests.proposal_decision_fixtures import write_v3_proposal
from p2p_engine.services.lifecycle_authority import ProposalLifecycleAuthorityService
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    render_decision_projection,
    render_proposal_projection,
)
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.services.workspace_reads import WorkspaceReadContext


pytestmark = pytest.mark.unit


_ALLOWED = {
    ProposalDecisionEffectiveState.undecided: {
        ProposalDecisionEventType.accepted,
        ProposalDecisionEventType.accepted_with_changes,
        ProposalDecisionEventType.deferred,
        ProposalDecisionEventType.withdrawn,
        ProposalDecisionEventType.rejected,
        ProposalDecisionEventType.split,
        ProposalDecisionEventType.merged_into_other,
    },
    ProposalDecisionEffectiveState.deferred: {
        ProposalDecisionEventType.accepted,
        ProposalDecisionEventType.accepted_with_changes,
        ProposalDecisionEventType.withdrawn,
        ProposalDecisionEventType.rejected,
        ProposalDecisionEventType.split,
        ProposalDecisionEventType.merged_into_other,
    },
    ProposalDecisionEffectiveState.accepted: {
        ProposalDecisionEventType.revoked,
        ProposalDecisionEventType.superseded,
        ProposalDecisionEventType.split,
        ProposalDecisionEventType.merged_into_other,
    },
    ProposalDecisionEffectiveState.accepted_with_changes: {
        ProposalDecisionEventType.revoked,
        ProposalDecisionEventType.superseded,
        ProposalDecisionEventType.split,
        ProposalDecisionEventType.merged_into_other,
    },
    ProposalDecisionEffectiveState.revoked: {
        ProposalDecisionEventType.reinstated,
    },
    ProposalDecisionEffectiveState.withdrawn: set(),
    ProposalDecisionEffectiveState.rejected: set(),
    ProposalDecisionEffectiveState.superseded: set(),
    ProposalDecisionEffectiveState.split: set(),
    ProposalDecisionEffectiveState.merged_into_other: set(),
}


@pytest.mark.parametrize(
    ("state", "event"),
    [
        (state, event)
        for state in ProposalDecisionEffectiveState
        if state != ProposalDecisionEffectiveState.undecided or True
        for event in ProposalDecisionEventType
    ],
)
def test_complete_transition_matrix(
    state: ProposalDecisionEffectiveState,
    event: ProposalDecisionEventType,
) -> None:
    expected = event in _ALLOWED.get(state, set())

    assert transition_allowed(state, event) is expected
    if expected:
        require_transition(state, event)
    else:
        with pytest.raises(ValueError, match="P2P363_DECISION_TRANSITION_INVALID"):
            require_transition(state, event)


def test_lifecycle_derives_closed_and_reinstated_authority_intervals() -> None:
    accepted, acceptance = ledger_with_acceptance()
    revoked, revocation = append_event(
        accepted,
        event_type=ProposalDecisionEventType.revoked,
        affected=acceptance,
        impact_required=True,
    )
    reinstated, reinstatement = append_event(
        revoked,
        event_type=ProposalDecisionEventType.reinstated,
        effective_state=ProposalDecisionEffectiveState.accepted,
        affected=acceptance,
        impact_required=True,
    )

    revoked_view = lifecycle_from_ledger(revoked)
    current_view = lifecycle_from_ledger(reinstated)

    assert revoked_view.active is False
    assert revoked_view.ever_active is True
    assert revoked_view.intervals[0].closed_by_event_id == revocation.event_id
    assert current_view.active is True
    assert current_view.effective_state == ProposalDecisionEffectiveState.accepted
    assert current_view.head_event_type == ProposalDecisionEventType.reinstated
    assert len(current_view.intervals) == 2
    assert current_view.intervals[1].opened_by_event_id == reinstatement.event_id
    assert current_view.intervals[1].active_event_id == acceptance.event_id


def test_diverged_binding_keeps_history_but_removes_active_projection() -> None:
    ledger, _ = ledger_with_acceptance()

    view = lifecycle_from_ledger(
        ledger,
        binding_status=ProposalDecisionBindingStatus.diverged,
    )

    assert view.active is True
    assert view.ever_active is True
    assert view.active_projection is False
    assert view.proposal_binding_status == ProposalDecisionBindingStatus.diverged


def test_reinstated_effective_state_must_restore_active_outcome() -> None:
    assert (
        effective_state_for_event(
            ProposalDecisionEventType.reinstated,
            restored_state=ProposalDecisionEffectiveState.accepted_with_changes,
        )
        == ProposalDecisionEffectiveState.accepted_with_changes
    )
    with pytest.raises(ValueError, match="P2P368_DECISION_REINSTATEMENT_MISMATCH"):
        effective_state_for_event(
            ProposalDecisionEventType.reinstated,
            restored_state=ProposalDecisionEffectiveState.rejected,
        )


@pytest.mark.parametrize(
    "state",
    (
        ProposalDecisionEffectiveState.rejected,
        ProposalDecisionEffectiveState.withdrawn,
    ),
)
def test_rejected_or_withdrawn_reconsideration_requires_new_proposal(
    state: ProposalDecisionEffectiveState,
) -> None:
    command = decision_reconsideration_command("PROP-001", state)

    assert command == (
        'p2p proposal create "Reconsidered direction for PROP-001"'
    )
    assert (
        decision_reconsideration_command(
            "PROP-001",
            ProposalDecisionEffectiveState.revoked,
        )
        is None
    )


def test_workspace_aware_service_rejects_non_current_schema(tmp_path) -> None:
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    proposal = proposals.create("Legacy View")
    service = ProposalLifecycleAuthorityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=proposals.find_dir,
        workspace_schema_status=lambda: type(
            "Schema",
            (),
            {"current_version": 2, "layout_status": "current", "recovery": {}},
        )(),
    )

    view = service.status(proposal.proposal_id)

    assert view.source_model == "unsupported_workspace"
    assert view.authority_resolution == ProposalDecisionAuthorityResolution.invalid
    assert view.effective_state == ProposalDecisionEffectiveState.undecided


def test_workspace_aware_v3_service_uses_ledger_over_corrupt_projection(tmp_path) -> None:
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    proposal = proposals.create("Ledger View")
    proposal_dir = tmp_path / proposal.path
    ledger, event = ledger_with_acceptance()
    codec = ProposalDecisionLedgerCodec()
    proposal_text = (proposal_dir / "proposal.md").read_text(encoding="utf-8")
    (proposal_dir / "decision-events.yml").write_bytes(codec.dumps(ledger))
    (proposal_dir / "proposal.md").write_text(
        render_proposal_projection(proposal_text, ledger.effective_state),
        encoding="utf-8",
    )
    (proposal_dir / "decision.md").write_text(
        render_decision_projection("PROP-001", event).replace(
            "`accepted`",
            "`rejected`",
            1,
        ),
        encoding="utf-8",
    )
    service = ProposalLifecycleAuthorityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=proposals.find_dir,
        workspace_schema_status=lambda: type(
            "Schema",
            (),
            {"current_version": 3, "layout_status": "current", "recovery": {}},
        )(),
    )

    view = service.status("PROP-001")

    assert view.effective_state == ProposalDecisionEffectiveState.accepted
    assert view.active is True
    assert any("P2P362_DECISION_PROJECTION_DIVERGENCE" in item for item in view.diagnostics)


def test_workspace_aware_v3_service_fails_closed_when_ledger_missing(tmp_path) -> None:
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    proposal = proposals.create("Missing Ledger")
    service = ProposalLifecycleAuthorityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=proposals.find_dir,
        workspace_schema_status=lambda: type(
            "Schema",
            (),
            {"current_version": 3, "layout_status": "current", "recovery": {}},
        )(),
    )

    view = service.status(proposal.proposal_id)

    assert view.authority_resolution.value == "invalid"
    assert view.active is False
    with pytest.raises(ValueError, match="missing decision-events.yml"):
        service.status(proposal.proposal_id, strict=True)


def test_lifecycle_map_is_stable_for_one_hundred_proposals(tmp_path) -> None:
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(
        "workspace_schema:\n  current_version: 3\n",
        encoding="utf-8",
    )
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    codec = ProposalDecisionLedgerCodec()
    for number in reversed(range(1, 101)):
        proposal_id = f"PROP-{number:03d}"
        ledger = (
            ledger_with_acceptance(proposal_id)[0]
            if number % 2
            else codec.empty(proposal_id)
        )
        proposal_dir = (
            tmp_path
            / ".p2p"
            / "proposals"
            / f"{proposal_id}-lifecycle-scale"
        )
        write_v3_proposal(proposal_dir, ledger)
        (proposal_dir / "decision.md").write_text(
            render_decision_projection(
                proposal_id,
                ledger.events[-1] if ledger.events else None,
                empty_state=ledger.effective_state,
            ),
            encoding="utf-8",
        )
    service = ProposalLifecycleAuthorityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=proposals.find_dir,
        workspace_schema_status=lambda: type(
            "Schema",
            (),
            {"current_version": 3, "layout_status": "current", "recovery": {}},
        )(),
    )

    lifecycles = service.capture_all(strict=True)

    assert list(lifecycles) == [
        f"PROP-{number:03d}" for number in range(1, 101)
    ]
    assert sum(item.active for item in lifecycles.values()) == 50


def test_lifecycle_batch_resolves_schema_and_directories_once(tmp_path: Path) -> None:
    schema_path = tmp_path / ".p2p/project/workspace-schema.yml"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text("workspace_schema:\n  current_version: 3\n", encoding="utf-8")
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    codec = ProposalDecisionLedgerCodec()
    for number in range(1, 11):
        proposal_id = f"PROP-{number:03d}"
        write_v3_proposal(
            tmp_path / ".p2p/proposals" / f"{proposal_id}-batch",
            codec.empty(proposal_id),
        )
    calls = 0

    def schema() -> object:
        nonlocal calls
        calls += 1
        return type(
            "Schema",
            (),
            {"current_version": 3, "layout_status": "current", "recovery": {}},
        )()

    service = ProposalLifecycleAuthorityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=proposals.find_dir,
        workspace_schema_status=schema,
    )

    values = service.evaluate_many([f"PROP-{number:03d}" for number in range(1, 11)])

    assert len(values) == 10
    assert calls == 1


def test_lifecycle_batch_reuses_captured_ledgers_within_read_context(
    tmp_path: Path,
) -> None:
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    codec = ProposalDecisionLedgerCodec()
    for number in range(1, 11):
        proposal_id = f"PROP-{number:03d}"
        ledger = codec.empty(proposal_id)
        proposal_dir = tmp_path / ".p2p/proposals" / f"{proposal_id}-batch"
        write_v3_proposal(proposal_dir, ledger)
        (proposal_dir / "decision.md").write_text(
            render_decision_projection(
                proposal_id,
                None,
                empty_state=ledger.effective_state,
            ),
            encoding="utf-8",
        )
    service = ProposalLifecycleAuthorityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=proposals.find_dir,
        workspace_schema_status=lambda: type(
            "Schema",
            (),
            {"current_version": 3, "layout_status": "current", "recovery": {}},
        )(),
    )
    context = WorkspaceReadContext(tmp_path)

    first = service.capture_all(read_context=context)
    second = service.capture_all(read_context=context)

    assert first == second
    assert context.counters.schema_preflights == 1
    assert len(context.counters.ledger_parses) == 10
    assert set(context.counters.ledger_parses.values()) == {1}
    assert context.counters.provider_calls["proposal_lifecycle_batch"] == 2
    assert context.counters.provider_cache_hits["proposal_lifecycle_batch"] == 1
    assert context.counters.discovery_passes == {
        ".p2p/proposals:proposal-directories-v1": 1
    }
