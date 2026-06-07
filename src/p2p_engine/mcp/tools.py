from __future__ import annotations

from pathlib import Path
from typing import Any

from p2p_engine.mcp.handlers.collaboration import handle_collaboration_tool
from p2p_engine.mcp.handlers.maintenance import handle_maintenance_tool
from p2p_engine.mcp.handlers.proposals import handle_proposal_tool
from p2p_engine.mcp.handlers.project import handle_project_tool
from p2p_engine.mcp.handlers.work_specs import handle_work_spec_tool
from p2p_engine.mcp.registry import TOOL_NAMES, tool_definitions
from p2p_engine.storage.filesystem import P2PWorkspace


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, object]:
    arguments = arguments or {}
    root = Path(str(arguments.get("root") or Path.cwd()))
    workspace = P2PWorkspace(root)
    handled = handle_maintenance_tool(workspace, name, arguments)
    if handled is not None:
        return handled
    handled = handle_project_tool(workspace, name, arguments)
    if handled is not None:
        return handled
    handled = handle_proposal_tool(workspace, name, arguments)
    if handled is not None:
        return handled
    handled = handle_collaboration_tool(workspace, name, arguments)
    if handled is not None:
        return handled
    handled = handle_work_spec_tool(workspace, name, arguments)
    if handled is not None:
        return handled

    raise ValueError(f"Unknown MCP tool: {name}")
