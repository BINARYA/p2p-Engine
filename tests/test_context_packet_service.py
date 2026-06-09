from pathlib import Path

import pytest

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace_with_context_items(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Context Project", project_domain="software")
    proposal = workspace.create_proposal_with_details(
        "Context Proposal",
        problem="This problem should appear in medium context.",
        proposal="This proposal should appear in medium context.",
    )
    workspace._choice_lifecycle_service().create("Context Choice", ["A", "B"], related=[proposal.proposal_id])
    workspace.record_decision(proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")
    change = workspace.create_change_set(proposal.proposal_id)
    workspace.refresh_software_spec(change.change_id)
    workspace.export_software_spec(change.change_id, "generic")
    workspace.create_work_plan(change.change_id, "generic")
    return workspace


def test_context_packet_service_builds_small_default_packet(tmp_path: Path) -> None:
    workspace = _workspace_with_context_items(tmp_path)
    packet = workspace._context_packet_service().context_packet()

    assert packet.budget == "small"
    assert packet.target is None
    assert packet.current_state["project"] == "Context Project"
    assert packet.current_state["proposals"] == 1
    assert packet.current_state["choices"] == 1
    assert packet.current_state["changes"] == 1
    assert packet.current_state["work_items"] == 1
    assert packet.current_state["interaction_style"]["technical_verbosity"]["value"] == 2
    assert packet.current_state["interaction_style"]["formality"]["value"] == 2
    assert packet.current_state["interaction_style"]["assertiveness"]["value"] == 0
    assert packet.current_state["interaction_style"]["update_command"].startswith("p2p project interaction-style set")
    assert packet.allowed_commands[:4] == [
        "p2p context --budget small",
        "p2p next --top 1",
        "p2p validate",
        "p2p assess show",
    ]
    assert "p2p project interaction-style show" in packet.allowed_commands
    assert "p2p proposal list" in packet.allowed_commands
    assert packet.bounded_next_step
    assert any("Do not scan all .p2p" in item for item in packet.do_not_read)


def test_context_packet_service_builds_medium_proposal_target(tmp_path: Path) -> None:
    workspace = _workspace_with_context_items(tmp_path)

    packet = workspace._context_packet_service().context_packet(budget="medium", target="prop-001")
    artifact = packet.relevant_artifacts[0]

    assert packet.target == "PROP-001"
    assert packet.bounded_next_step == "p2p proposal show PROP-001"
    assert packet.allowed_commands[:2] == [
        "p2p proposal show PROP-001",
        "p2p context --target PROP-001 --budget medium",
    ]
    assert artifact["type"] == "proposal"
    assert artifact["id"] == "PROP-001"
    assert artifact["problem"] == "This problem should appear in medium context."
    assert artifact["proposal"] == "This proposal should appear in medium context."
    assert artifact["artifact_coverage"]["status"] == "active"
    assert any(gap["artifact"] == "open_questions" for gap in artifact["artifact_coverage"]["gaps"])


def test_context_packet_service_builds_change_choice_and_work_targets(tmp_path: Path) -> None:
    workspace = _workspace_with_context_items(tmp_path)
    service = workspace._context_packet_service()

    change = service.context_packet(target="CHANGE-001").relevant_artifacts[0]
    choice = service.context_packet(target="CHOICE-001").relevant_artifacts[0]
    work = service.context_packet(target="WORK-001").relevant_artifacts[0]

    assert change["type"] == "change"
    assert change["command"] == "p2p change show CHANGE-001"
    assert choice["type"] == "choice"
    assert choice["options_count"] == 2
    assert work["type"] == "work"
    assert work["command"] == "p2p work show WORK-001"


def test_context_packet_service_rejects_invalid_budget(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Context Project")

    with pytest.raises(ValueError, match="Context budget must be small or medium"):
        workspace._context_packet_service().context_packet(budget="large")


def test_context_packet_service_rejects_invalid_target_prefix(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Context Project")

    with pytest.raises(ValueError, match="Context target must start"):
        workspace._context_packet_service().context_packet(target="BAD-001")
