from __future__ import annotations

from typing import Any

from p2p_engine.mcp.handlers.collaboration_proposals import handle_collaboration_proposal_tool
from p2p_engine.mcp.handlers.collaboration_remote import handle_collaboration_remote_tool
from p2p_engine.mcp.handlers.collaboration_sync import handle_collaboration_sync_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_collaboration_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    handled = handle_collaboration_remote_tool(workspace, name, arguments)
    if handled is not None:
        return handled
    handled = handle_collaboration_sync_tool(workspace, name, arguments)
    if handled is not None:
        return handled
    return handle_collaboration_proposal_tool(workspace, name, arguments)
