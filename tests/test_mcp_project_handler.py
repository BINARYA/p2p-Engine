from __future__ import annotations

from pathlib import Path

from p2p_engine.mcp.handlers.project import handle_project_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(tmp_path: Path) -> P2PWorkspace:
    call_tool("p2p_init_project", {"root": str(tmp_path), "name": "Demo Project"})
    return P2PWorkspace(tmp_path)


def test_mcp_project_handler_returns_none_for_other_domains(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    assert handle_project_tool(workspace, "p2p_proposal_create", {}) is None


def test_mcp_project_handler_serves_context_and_registry_tools(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    context = handle_project_tool(workspace, "p2p_context", {"budget": "small"})
    registry = handle_project_tool(workspace, "p2p_registry_status", {})
    validation = handle_project_tool(workspace, "p2p_validate", {})

    assert context is not None
    assert "context" in context
    assert registry is not None
    assert "registry_status" in registry
    assert validation is not None
    assert "validation" in validation


def test_mcp_call_tool_uses_project_handler(tmp_path: Path) -> None:
    _workspace(tmp_path)

    result = call_tool("p2p_project_status", {"root": str(tmp_path)})

    assert "project_status" in result
