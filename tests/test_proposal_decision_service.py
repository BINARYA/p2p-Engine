from __future__ import annotations

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.proposal_decisions import ProposalDecisionService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.storage.filesystem import P2PWorkspace


def _services(tmp_path):
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    decisions = ProposalDecisionService(root=tmp_path, p2p_dir=tmp_path / ".p2p", find_proposal_dir=proposals.find_dir)
    return proposals, decisions


def test_proposal_decision_service_records_decision_markdown_and_status(tmp_path) -> None:
    proposals, decisions = _services(tmp_path)
    proposal = proposals.create("Decision Service")

    decision = decisions.record(proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")
    proposal_dir = tmp_path / proposal.path
    decision_text = (proposal_dir / "decision.md").read_text(encoding="utf-8")
    proposal_text = (proposal_dir / "proposal.md").read_text(encoding="utf-8")

    assert decision.proposal_id == proposal.proposal_id
    assert decision.outcome == DecisionOutcome.accepted
    assert decision.reason == "Ready."
    assert decision.approver == "owner"
    assert "# Decision - PROP-001" in decision_text
    assert "## Status\n\n`accepted`" in decision_text
    assert "## Outcome\n\naccepted" in decision_text
    assert "## Reason\n\nReady." in decision_text
    assert "## Approver\n\nowner" in decision_text
    assert "## Status\n\n`accepted`" in proposal_text


def test_proposal_decision_service_preserves_non_accept_outcomes(tmp_path) -> None:
    proposals, decisions = _services(tmp_path)
    rejected = proposals.create("Rejected Decision")
    deferred = proposals.create("Deferred Decision")

    rejected_decision = decisions.record(rejected.proposal_id, DecisionOutcome.rejected, "Out of scope.", "owner")
    deferred_decision = decisions.record(deferred.proposal_id, DecisionOutcome.deferred, "Needs context.", "reviewer")

    assert rejected_decision.outcome == DecisionOutcome.rejected
    assert rejected_decision.reason == "Out of scope."
    assert rejected_decision.approver == "owner"
    assert deferred_decision.outcome == DecisionOutcome.deferred
    assert deferred_decision.reason == "Needs context."
    assert deferred_decision.approver == "reviewer"


def test_workspace_record_decision_facade_delegates_to_service(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Decision Facade")
    proposal = workspace.create_proposal("Facade Decision")

    decision = workspace.record_decision(proposal.proposal_id, DecisionOutcome.accepted, "Facade works.", "owner")
    detail = workspace.show_proposal(proposal.proposal_id)

    assert decision.proposal_id == proposal.proposal_id
    assert decision.outcome == DecisionOutcome.accepted
    assert detail.status == "accepted"
    assert detail.decision_status == "accepted"
    assert detail.decision_reason == "Facade works."
