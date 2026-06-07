from __future__ import annotations

from pathlib import Path

from p2p_engine.mcp.handlers.maintenance import handle_maintenance_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def test_mcp_maintenance_handler_returns_none_for_other_domains(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    assert handle_maintenance_tool(workspace, "p2p_context", {}) is None


def test_mcp_maintenance_handler_initializes_project_and_serves_next_actions(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    initialized = handle_maintenance_tool(
        workspace,
        "p2p_init_project",
        {"name": "Maintenance Project", "agent": "generic"},
    )
    added = handle_maintenance_tool(
        workspace,
        "p2p_next_add",
        {
            "kind": "verify_integration",
            "target": "mcp",
            "reason": "Cover maintenance handler.",
        },
    )
    assert added is not None
    action_id = added["next_action"]["action_id"]
    completed = handle_maintenance_tool(
        workspace,
        "p2p_next_complete",
        {"action_id": action_id, "reason": "Covered."},
    )

    assert initialized is not None
    assert initialized["initialized"] is True
    assert action_id.startswith("NEXT-")
    assert completed is not None
    assert completed["next_action_result"]["action"]["status"] == "completed"


def test_mcp_maintenance_handler_serves_agent_and_refresh_tools(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    handle_maintenance_tool(workspace, "p2p_init_project", {"name": "Maintenance Project"})

    installed = handle_maintenance_tool(workspace, "p2p_agent_install", {"adapter": "gemini"})
    registry = handle_maintenance_tool(workspace, "p2p_registry_refresh", {})
    assessment = handle_maintenance_tool(workspace, "p2p_assess_refresh", {})
    maturity = handle_maintenance_tool(workspace, "p2p_maturity_refresh", {})

    assert installed is not None
    assert installed["agent_integration"]["target"] == "gemini"
    assert registry is not None
    assert "written" in registry
    assert assessment is not None
    assert "assessment" in assessment
    assert maturity is not None
    assert "maturity" in maturity


def test_mcp_call_tool_uses_maintenance_handler(tmp_path: Path) -> None:
    result = call_tool("p2p_init_project", {"root": str(tmp_path), "name": "Facade Project"})

    assert result["initialized"] is True
