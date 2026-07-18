from __future__ import annotations

import re

import pytest
import yaml

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionCondition,
    ProposalDecisionEffectiveState,
    ProposalDecisionEventType,
    ProposalDecisionLineage,
    ProposalDecisionLineageKind,
)
from p2p_engine.services.proposal_decision_ledger import (
    EVENT_INTEGRITY_POLICY_VERSION,
    MAX_RATIONALE_BYTES,
    ProposalDecisionLedgerCodec,
    operation_key,
    projection_binding_status,
    proposal_semantic_sha256,
    render_decision_projection,
    render_proposal_projection,
    strict_yaml_load,
)
from tests.proposal_decision_fixtures import (
    append_event,
    ledger_with_acceptance,
    proposal_markdown,
)


pytestmark = pytest.mark.unit


def test_event_integrity_policy_version_is_explicit() -> None:
    assert EVENT_INTEGRITY_POLICY_VERSION == 1


def test_empty_ledger_round_trip_is_canonical() -> None:
    codec = ProposalDecisionLedgerCodec()
    ledger = codec.empty("PROP-001")

    content = codec.dumps(ledger)
    parsed = codec.loads(content, expected_proposal_id="PROP-001")

    assert parsed == ledger
    assert content == codec.dumps(parsed)
    assert parsed.effective_state == ProposalDecisionEffectiveState.undecided
    assert parsed.head_event_id is None
    assert parsed.events == ()


def test_strict_yaml_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate YAML key"):
        strict_yaml_load(b"root:\n  value: one\n  value: two\n")


def test_proposal_fingerprint_ignores_projection_status_and_newline_style() -> None:
    first = proposal_markdown(status="draft")
    second = proposal_markdown(status="accepted").replace("\n", "\r\n")

    assert proposal_semantic_sha256("PROP-001", first) == proposal_semantic_sha256(
        "PROP-001",
        second,
    )


def test_proposal_fingerprint_normalizes_markdown_bullet_marker() -> None:
    first = proposal_markdown()
    second = first.replace("- Preserve decisions.", "* Preserve decisions.")

    assert proposal_semantic_sha256("PROP-001", first) == proposal_semantic_sha256(
        "PROP-001",
        second,
    )


def test_proposal_fingerprint_rejects_duplicate_semantic_section() -> None:
    duplicate = proposal_markdown() + "\n## Problem\n\nA second problem.\n"

    with pytest.raises(ValueError, match="duplicate semantic section"):
        proposal_semantic_sha256("PROP-001", duplicate)


def test_event_chain_round_trip_and_tamper_detection() -> None:
    codec = ProposalDecisionLedgerCodec()
    accepted, event = ledger_with_acceptance()
    revoked, _ = append_event(
        accepted,
        event_type=ProposalDecisionEventType.revoked,
        affected=event,
        impact_required=True,
    )

    content = codec.dumps(revoked)
    assert codec.loads(content) == revoked

    payload = yaml.safe_load(content)
    payload["proposal_decision_ledger"]["events"][0]["rationale"] = "Tampered."
    with pytest.raises(ValueError, match="event hash mismatch"):
        codec.loads(yaml.safe_dump(payload, sort_keys=False).encode())


def test_chain_rejects_wrong_head_and_backdated_successor() -> None:
    codec = ProposalDecisionLedgerCodec()
    accepted, event = ledger_with_acceptance()
    payload = accepted.to_dict()
    payload["proposal_decision_ledger"]["head_event_id"] = None
    with pytest.raises(ValueError, match="head_event_id"):
        codec.loads(yaml.safe_dump(payload, sort_keys=False).encode())

    with pytest.raises(ValueError, match="non-decreasing"):
        append_event(
            accepted,
            event_type=ProposalDecisionEventType.revoked,
            affected=event,
            impact_required=True,
            decided_on="2026-07-16",
        )


def test_event_identity_is_deterministic_and_path_independent() -> None:
    first, first_event = ledger_with_acceptance()
    second, second_event = ledger_with_acceptance()

    assert first == second
    assert first_event.event_id == second_event.event_id
    assert re.fullmatch(r"PDE-[0-9a-f]{24}", first_event.event_id)
    assert len(first_event.event_sha256) == 64


def test_operation_key_binds_source_head() -> None:
    semantics = {"proposal_id": "PROP-001", "event_type": "accepted"}

    assert operation_key(semantics, None) == operation_key(semantics, None)
    assert operation_key(semantics, None) != operation_key(
        semantics,
        "PDE-" + "0" * 24,
    )


def test_accepted_with_changes_requires_structured_conditions() -> None:
    codec = ProposalDecisionLedgerCodec()
    with pytest.raises(ValueError, match="structured condition"):
        append_event(
            codec.empty("PROP-001"),
            event_type=ProposalDecisionEventType.accepted_with_changes,
        )

    ledger, event = append_event(
        codec.empty("PROP-001"),
        event_type=ProposalDecisionEventType.accepted_with_changes,
        conditions=(ProposalDecisionCondition("C001", "Apply the compatibility gate."),),
    )
    assert ledger.effective_state == ProposalDecisionEffectiveState.accepted_with_changes
    assert event.conditions[0].condition_id == "C001"


def test_lineage_cardinality_and_self_target_are_rejected() -> None:
    codec = ProposalDecisionLedgerCodec()
    with pytest.raises(ValueError, match="requires split lineage"):
        append_event(
            codec.empty("PROP-001"),
            event_type=ProposalDecisionEventType.split,
            lineage=ProposalDecisionLineage(
                ProposalDecisionLineageKind.split,
                ("PROP-002",),
            ),
        )
    with pytest.raises(ValueError, match="cannot target itself"):
        append_event(
            codec.empty("PROP-001"),
            event_type=ProposalDecisionEventType.merged_into_other,
            lineage=ProposalDecisionLineage(
                ProposalDecisionLineageKind.merged_into,
                ("PROP-001",),
            ),
        )


def test_projection_rendering_and_binding_detection() -> None:
    ledger, event = ledger_with_acceptance()
    proposal = proposal_markdown()

    proposal_projection = render_proposal_projection(proposal, ledger.effective_state)
    decision_projection = render_decision_projection("PROP-001", event)

    assert "## Status\n\n`accepted`" in proposal_projection
    assert "## Event Type\n\naccepted" in decision_projection
    assert f"## Ledger Head\n\n{event.event_id}" in decision_projection
    assert "## Canonical Source\n\ndecision-events.yml" in decision_projection
    assert projection_binding_status("PROP-001", proposal_projection, event).value == "current"
    changed = proposal_projection.replace(
        "Use an append-only ledger.",
        "Use an overwrite-only record.",
    )
    assert projection_binding_status("PROP-001", changed, event).value == "diverged"


def test_limits_fail_before_identity_calculation() -> None:
    with pytest.raises(ValueError, match=f"maximum is {MAX_RATIONALE_BYTES}"):
        append_event(
            ProposalDecisionLedgerCodec().empty("PROP-001"),
            event_type=ProposalDecisionEventType.accepted,
            reason="x" * (MAX_RATIONALE_BYTES + 1),
        )


def test_future_contract_fails_closed() -> None:
    payload = ProposalDecisionLedgerCodec().empty("PROP-001").to_dict()
    payload["proposal_decision_ledger"]["contract_version"] = 99

    with pytest.raises(ValueError, match="P2P376_DECISION_FUTURE_CONTRACT"):
        ProposalDecisionLedgerCodec().loads(
            yaml.safe_dump(payload, sort_keys=False).encode()
        )
