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
