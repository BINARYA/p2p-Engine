from __future__ import annotations

from typing import Any

from p2p_engine.mcp.handlers.collaboration_access import handle_collaboration_access_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_collaboration_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    return handle_collaboration_access_tool(workspace, name, arguments)
