from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project", project_domain="software")
    return workspace


def test_next_action_service_manages_curated_lifecycle(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._next_action_service()

    action = service.add(
        kind="verify_integration",
        target="mcp-client",
        priority="high",
        reason="Verify real MCP client setup.",
        command="p2p-mcp-server --root /path/to/project",
    )
    listed = service.list(limit=1)
    result = service.complete(action.action_id, "Verified successfully.")

    assert action.action_id == "NEXT-001"
    assert listed[0].kind == "verify_integration"
    assert listed[0].source == ".p2p/project/next-actions.yml"
    assert result["action"]["status"] == "completed"
    assert result["path"] == ".p2p/project/next-actions-log.yml"
    active = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions.yml").read_text(encoding="utf-8"))
    log = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions-log.yml").read_text(encoding="utf-8"))
    assert active["next_actions"] == []
    assert log["next_action_log"][0]["id"] == "NEXT-001"
    assert log["next_action_log"][0]["closed_reason"] == "Verified successfully."


def test_next_action_service_refreshes_and_dedupes_generated_actions(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._next_action_service()
    service.add(
        kind="refresh_registry",
        target="registries",
        priority="medium",
        reason="Curated registry refresh.",
    )

    refreshed = service.refresh()
    actions = service.list()
    refresh_actions = [
        action for action in actions if action.kind == "refresh_registry" and action.target == "registries"
    ]

    assert refreshed["active_curated"] == 1
    assert refreshed["generated"] >= 1
    assert len(refresh_actions) == 1
    assert refresh_actions[0].source == ".p2p/project/next-actions.yml"


def test_next_action_service_prioritizes_active_choice_blockers(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Governance Model")
    workspace.record_decision("PROP-001", DecisionOutcome.accepted, "Needed.", "owner")
    workspace.create_change_set("PROP-001", "Governance Model")
    workspace.update_change_set_status("CHANGE-001", "planned")
    workspace.create_choice(
        "Governance Scope",
        ["Minimal governance", "Full governance"],
        related=["PROP-001"],
    )
    workspace.block_choice(
        "CHOICE-001",
        target="CHANGE-001",
        target_type="change",
        reason="Governance scope must be decided first.",
    )

    action = workspace._next_action_service().list(limit=1)[0]

    assert action.action_id == "NEXT-BLOCKER-001"
    assert action.priority == "high"
    assert action.kind == "resolve_choice"
    assert action.target == "CHOICE-001"
    assert "blocks change CHANGE-001" in action.reason


def test_next_actions_distinguish_project_choices_from_proposal_local_votes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Local Vote")
    workspace.record_vote(
        proposal.proposal_id,
        choice="A",
        reason="Proposal-local preference only.",
        voter="owner",
        role="owner",
    )

    actions = workspace._next_action_service().list()

    assert not any(
        action.kind == "resolve_choice" and action.target.startswith("CHOICE-PROP-")
        for action in actions
    )
    assert not any(
        node.node_id.startswith("CHOICE-PROP-")
        for node in workspace.decision_context_index().nodes
    )


def test_next_actions_resolve_only_open_normalized_project_choices(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    choice = workspace.create_choice("Project Choice", ["A", "B"])

    open_actions = workspace._next_action_service().list()
    workspace.decide_choice(choice.choice_id, "A", "A is selected.", "owner")
    decided_actions = workspace._next_action_service().list()

    assert any(
        action.kind == "resolve_choice" and action.target == choice.choice_id
        for action in open_actions
    )
    assert not any(
        action.kind == "resolve_choice" and action.target == choice.choice_id
        for action in decided_actions
    )


def test_decided_choice_with_missing_target_has_no_active_edge_or_action(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    choice = workspace.create_choice("Missing Target Choice", ["A", "B"])
    workspace.decide_choice(choice.choice_id, "A", "A is selected.", "owner")
    choice_dir = tmp_path / choice.path
    (choice_dir / "links.yml").write_text(
        "related_proposals:\n"
        "  - proposal: PROP-999\n"
        "    relationship: related_to\n",
        encoding="utf-8",
    )

    index = workspace.decision_context_index()
    actions = workspace._next_action_service().list()

    assert any(
        diagnostic.code == "DC-RELATION-INVALID-TARGET"
        and diagnostic.target_id == "PROP-999"
        for diagnostic in index.diagnostics
    )
    assert not any(relation.target_id == "PROP-999" for relation in index.relations)
    assert not any(action.target == choice.choice_id for action in actions)


def test_next_actions_use_normalized_change_proposal_relationships(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Change Relationship")
    workspace.record_decision(proposal.proposal_id, DecisionOutcome.accepted, "Needed.", "owner")
    change = workspace.create_change_set(proposal.proposal_id, "Change Relationship")
    workspace.update_change_set_status(change.change_id, "planned")

    action = next(
        action
        for action in workspace._next_action_service().list()
        if action.kind == "continue_change"
    )

    assert action.target == change.change_id
    assert f"Included proposals: {proposal.proposal_id}." in action.reason


def test_historical_conflicts_and_legacy_projection_do_not_create_choice_actions(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    first = workspace.create_proposal("Current Direction")
    second = workspace.create_proposal("Historical Direction")
    workspace.record_decision(second.proposal_id, DecisionOutcome.rejected, "Historical.", "owner")
    (tmp_path / ".p2p" / "project" / "conflicts.yml").write_text(
        "conflicts:\n"
        f"  - proposals: [{first.proposal_id}, {second.proposal_id}]\n",
        encoding="utf-8",
    )
    registries = tmp_path / ".p2p" / "registries"
    registries.mkdir(exist_ok=True)
    (registries / "relations.yml").write_text(
        "relations:\n"
        "  - source: CHOICE-FAKE\n"
        "    target: PROP-001\n"
        "    type: blocks\n",
        encoding="utf-8",
    )

    actions = workspace._next_action_service().list()
    index = workspace.decision_context_index()

    assert not any(action.kind == "resolve_choice" for action in actions)
    assert not any(source.path.endswith("registries/relations.yml") for source in index.sources)


def test_next_actions_fall_back_to_project_review_when_no_semantic_work_exists(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    workspace.refresh_registries()

    actions = workspace._next_action_service().list()

    assert [(action.kind, action.target) for action in actions] == [("review_project", "project")]


def test_next_action_service_rejects_invalid_payload_shapes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._next_action_service()
    next_actions_path = tmp_path / ".p2p" / "project" / "next-actions.yml"
    next_actions_path.write_text("next_actions: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="next_actions must be a list"):
        service.add(kind="verify", target="target", reason="Invalid active payload.")

    next_actions_path.write_text(
        "next_actions:\n"
        "  - id: NEXT-001\n"
        "    kind: verify\n"
        "    reason: Valid active payload.\n",
        encoding="utf-8",
    )
    (tmp_path / ".p2p" / "project" / "next-actions-log.yml").write_text(
        "next_action_log: {}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="next_action_log must be a list"):
        service.retire("NEXT-001", "Invalid log payload.")
