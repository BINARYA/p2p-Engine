from __future__ import annotations

import os

import pytest

from p2p_engine.services.proposal_decision_legacy import ProposalDecisionLegacyAdapter
from p2p_engine.services.proposals import ProposalDocumentService


pytestmark = pytest.mark.service


def _proposal(tmp_path):
    service = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    proposal = service.create("Legacy Decision")
    return tmp_path / proposal.path


def test_pending_v2_proposal_is_readable_and_undecided(tmp_path) -> None:
    proposal_dir = _proposal(tmp_path)
    adapter = ProposalDecisionLegacyAdapter()

    snapshot = adapter.capture(
        proposal_id="PROP-001",
        proposal_path=proposal_dir / "proposal.md",
        decision_path=proposal_dir / "decision.md",
        root=tmp_path,
    )
    view = adapter.lifecycle(snapshot)

    assert snapshot.normalized_state == "undecided"
    assert view.source_model == "legacy_projection_v2"
    assert view.effective_state.value == "undecided"
    assert view.active is False


def test_aligned_legacy_acceptance_requires_explicit_authority_fields(tmp_path) -> None:
    proposal_dir = _proposal(tmp_path)
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace("`draft`", "`accepted`"),
        encoding="utf-8",
    )
    (proposal_dir / "decision.md").write_text(
        "# Decision - PROP-001\n\n"
        "## Status\n\n`accepted`\n\n"
        "## Outcome\n\naccepted\n\n"
        "## Reason\n\nReady.\n\n"
        "## Date\n\n2026-07-17\n\n"
        "## Approver\n\nowner\n",
        encoding="utf-8",
    )

    adapter = ProposalDecisionLegacyAdapter()
    snapshot = adapter.capture(
        proposal_id="PROP-001",
        proposal_path=proposal_path,
        decision_path=proposal_dir / "decision.md",
        root=tmp_path,
    )
    view = adapter.lifecycle(snapshot)

    assert snapshot.aligned is True
    assert snapshot.authority_fields_complete is True
    assert view.authority_resolution.value == "resolved"
    assert view.active is True


def test_divergent_legacy_projection_is_unknown_and_preserved(tmp_path) -> None:
    proposal_dir = _proposal(tmp_path)
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace("`draft`", "`accepted`"),
        encoding="utf-8",
    )
    (proposal_dir / "decision.md").write_text(
        "# Decision - PROP-001\n\n"
        "## Status\n\n`rejected`\n\n"
        "## Outcome\n\nrejected\n\n"
        "## Reason\n\nNot suitable.\n",
        encoding="utf-8",
    )
    adapter = ProposalDecisionLegacyAdapter()
    snapshot = adapter.capture(
        proposal_id="PROP-001",
        proposal_path=proposal_path,
        decision_path=proposal_dir / "decision.md",
        root=tmp_path,
    )

    view = adapter.lifecycle(snapshot)
    evidence = adapter.legacy_evidence(snapshot)

    assert view.effective_state.value == "unknown_legacy"
    assert view.authority_resolution.value == "unknown_legacy"
    assert evidence.values["proposal_status"] == "accepted"
    assert evidence.values["decision_status"] == "rejected"
    assert "P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED" in evidence.diagnostics


def test_legacy_capture_does_not_use_mtime_or_process_identity(tmp_path, monkeypatch) -> None:
    proposal_dir = _proposal(tmp_path)
    proposal_path = proposal_dir / "proposal.md"
    decision_path = proposal_dir / "decision.md"
    os.utime(proposal_path, (1, 1))
    os.utime(decision_path, (2, 2))
    monkeypatch.setenv("USER", "not-the-owner")

    snapshot = ProposalDecisionLegacyAdapter().capture(
        proposal_id="PROP-001",
        proposal_path=proposal_path,
        decision_path=decision_path,
        root=tmp_path,
    )

    assert snapshot.approver == ""
    assert snapshot.decided_on == ""
    assert "not-the-owner" not in repr(snapshot)
