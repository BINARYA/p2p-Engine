from __future__ import annotations

from p2p_engine.core.proposal_decision_diagnostics import (
    PROPOSAL_DECISION_DIAGNOSTICS,
    proposal_decision_diagnostic,
)


def test_proposal_decision_diagnostic_range_is_complete_and_collision_free() -> None:
    assert len(PROPOSAL_DECISION_DIAGNOSTICS) == 29
    assert {
        int(code[3:6])
        for code in PROPOSAL_DECISION_DIAGNOSTICS
    } == set(range(361, 390))
    assert len(set(PROPOSAL_DECISION_DIAGNOSTICS)) == 29

    for code, definition in PROPOSAL_DECISION_DIAGNOSTICS.items():
        assert definition.code == code
        assert definition.title
        assert definition.severity in {"error", "warning"}
        assert definition.recovery


def test_proposal_decision_diagnostic_parses_messages_and_rejects_unknown_codes() -> None:
    stale = proposal_decision_diagnostic(
        "apply failed: P2P365_DECISION_STALE_PREVIEW: source changed"
    )

    assert stale is not None
    assert stale.code == "P2P365_DECISION_STALE_PREVIEW"
    assert "fresh preview" in stale.recovery
    reconsideration = proposal_decision_diagnostic(
        "P2P378_DECISION_RECONSIDERATION_REQUIRES_NEW_PROPOSAL"
    )
    assert reconsideration is not None
    assert reconsideration.severity == "warning"
    assert proposal_decision_diagnostic("P2P359_UNRELATED") is None
    assert proposal_decision_diagnostic("P2P389_DECISION_NOT_REGISTERED") is None
