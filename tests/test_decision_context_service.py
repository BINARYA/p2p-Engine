from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.decision_context import Activation, Authority, Completeness, RecordKind, to_json_ready
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.decision_context_fixtures import write_proposal


@pytest.mark.parametrize(
    ("outcome", "decision_authority", "decision_activation", "proposal_activation"),
    [
        ("accepted", Authority.ACCEPTED_DECISION, Activation.ACTIVE, Activation.ACTIVE),
        (
            "accepted_with_changes",
            Authority.CONDITIONALLY_ACCEPTED_DECISION,
            Activation.ACTIVE,
            Activation.ACTIVE,
        ),
        ("rejected", Authority.HISTORICAL_PROPOSAL, Activation.HISTORICAL, Activation.HISTORICAL),
        ("deferred", Authority.HISTORICAL_PROPOSAL, Activation.UNRESOLVED, Activation.HISTORICAL),
        ("split", Authority.HISTORICAL_PROPOSAL, Activation.HISTORICAL, Activation.HISTORICAL),
        ("merged_into_other", Authority.HISTORICAL_PROPOSAL, Activation.HISTORICAL, Activation.HISTORICAL),
        ("superseded", Authority.HISTORICAL_PROPOSAL, Activation.HISTORICAL, Activation.HISTORICAL),
        ("pending", Authority.UNKNOWN, Activation.UNRESOLVED, Activation.EXPLORATORY),
    ],
)
def test_decision_lifecycle_mapping(
    tmp_path: Path,
    outcome: str,
    decision_authority: Authority,
    decision_activation: Activation,
    proposal_activation: Activation,
) -> None:
    write_proposal(tmp_path, "PROP-001", status=outcome, decision_outcome=outcome)

    index = ProjectDecisionContextService(root=tmp_path).build_index()

    decision = next(record for record in index.records if record.kind == RecordKind.DECISION_STATE)
    proposal = next(record for record in index.records if record.kind == RecordKind.PROPOSAL_CLAIM)
    assert decision.authority == decision_authority
    assert decision.activation == decision_activation
    assert proposal.activation == proposal_activation


def test_conditional_acceptance_emits_qualifier_linked_to_proposal_claims(tmp_path: Path) -> None:
    write_proposal(
        tmp_path,
        "PROP-001",
        status="accepted_with_changes",
        decision_outcome="accepted_with_changes",
        decision_reason="Accept only with a read-only boundary.",
    )

    index = ProjectDecisionContextService(root=tmp_path).build_index()

    qualifier = next(record for record in index.records if record.kind == RecordKind.DECISION_QUALIFIER)
    proposal_claims = {record.record_id for record in index.records if record.kind == RecordKind.PROPOSAL_CLAIM}
    assert qualifier.text == "Accept only with a read-only boundary."
    assert proposal_claims.issubset(set(qualifier.related_record_ids))


def test_status_divergence_is_reported_without_source_repair(tmp_path: Path) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001", status="draft", decision_outcome="accepted")
    original = (proposal_dir / "proposal.md").read_text(encoding="utf-8")

    index = ProjectDecisionContextService(root=tmp_path).build_index()

    assert any(item.code == "DC-AUTHORITY-STATUS-DIVERGENCE" for item in index.diagnostics)
    assert (proposal_dir / "proposal.md").read_text(encoding="utf-8") == original


def test_decision_status_controls_state_and_free_form_outcome_is_preserved(tmp_path: Path) -> None:
    proposal_dir = write_proposal(
        tmp_path,
        "PROP-001",
        status="accepted",
        decision_outcome="accepted",
    )
    decision = proposal_dir / "decision.md"
    decision.write_text(
        decision.read_text(encoding="utf-8").replace(
            "## Outcome\n\naccepted",
            "## Outcome\n\nAdopt the compatibility-first architecture.",
        ),
        encoding="utf-8",
    )

    index = ProjectDecisionContextService(root=tmp_path).build_index()

    state = next(record for record in index.records if record.kind == RecordKind.DECISION_STATE)
    statement = next(record for record in index.records if record.kind == RecordKind.DECISION_STATEMENT)
    assert state.text == "accepted"
    assert statement.text == "Adopt the compatibility-first architecture."
    assert not any(item.code == "DC-AUTHORITY-UNKNOWN-DECISION-OUTCOME" for item in index.diagnostics)


def test_legacy_outcome_token_controls_state_when_status_is_unrecognized(tmp_path: Path) -> None:
    proposal_dir = write_proposal(
        tmp_path,
        "PROP-001",
        status="accepted",
        decision_outcome="accepted",
    )
    decision = proposal_dir / "decision.md"
    decision.write_text(
        decision.read_text(encoding="utf-8").replace("`accepted`", "`Decision recorded`", 1),
        encoding="utf-8",
    )

    index = ProjectDecisionContextService(root=tmp_path).build_index()

    state = next(record for record in index.records if record.kind == RecordKind.DECISION_STATE)
    assert state.text == "accepted"


def test_proposal_list_sections_become_independent_records(tmp_path: Path) -> None:
    write_proposal(
        tmp_path,
        "PROP-001",
        goals=("First goal.", "Second goal.\n  - Nested detail."),
        acceptance=("First criterion.", "Second criterion."),
    )

    index = ProjectDecisionContextService(root=tmp_path).build_index()

    goals = [record for record in index.records if record.kind == RecordKind.GOAL]
    criteria = [record for record in index.records if record.kind == RecordKind.ACCEPTANCE_CRITERION]
    assert [record.text for record in goals] == ["First goal.", "Second goal.\n  - Nested detail."]
    assert len(criteria) == 2
    assert len({record.record_id for record in goals}) == 2


def test_missing_required_section_makes_index_partial(tmp_path: Path) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001")
    path = proposal_dir / "proposal.md"
    text = path.read_text(encoding="utf-8")
    start = text.index("## Problem")
    end = text.index("## Goals")
    path.write_text(text[:start] + text[end:], encoding="utf-8")

    index = ProjectDecisionContextService(root=tmp_path).build_index()

    assert index.completeness == Completeness.PARTIAL
    assert any(item.code == "DC-SOURCE-MISSING-SECTION" for item in index.diagnostics)


def test_index_serialization_is_json_ready_and_hides_raw_source_bytes(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001", status="accepted", decision_outcome="accepted")
    index = ProjectDecisionContextService(root=tmp_path).build_index()

    serialized = to_json_ready(index)

    assert isinstance(serialized, dict)
    assert serialized["completeness"] == "complete"
    assert "_content" not in serialized["sources"][0]
    assert serialized["records"][0]["schema_version"] == "decision-context-v1"


def test_workspace_memoizes_stateless_service_but_not_index(tmp_path: Path) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001")
    workspace = P2PWorkspace(tmp_path)
    first_service = workspace._decision_context_service()
    first = workspace.decision_context_index()
    path = proposal_dir / "proposal.md"
    path.write_text(path.read_text(encoding="utf-8").replace("derived", "updated derived"), encoding="utf-8")
    second = workspace.decision_context_index()

    assert workspace._decision_context_service() is first_service
    assert first.source_fingerprint_sha256 != second.source_fingerprint_sha256
