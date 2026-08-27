from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.mcp.handlers.collaboration import handle_collaboration_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(tmp_path: Path) -> P2PWorkspace:
    call_tool(
        "p2p_init_project",
        {"root": str(tmp_path), "name": "Demo Project", "starter": "generic"},
    )
    return P2PWorkspace(tmp_path)


def test_mcp_collaboration_handler_returns_none_for_other_domains(
    tmp_path: Path,
) -> None:
    assert handle_collaboration_tool(_workspace(tmp_path), "p2p_context", {}) is None


def test_mcp_collaboration_handler_serves_permissions_and_consent(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)

    permissions = handle_collaboration_tool(workspace, "p2p_permissions_show", {})
    consent = handle_collaboration_tool(
        workspace,
        "p2p_consent_request",
        {
            "operation": "proposal_decision_apply",
            "target": "PROP-001@preview-token",
            "actor_id": "owner",
        },
    )
    consents = handle_collaboration_tool(workspace, "p2p_consent_status", {})

    assert permissions is not None and "permissions" in permissions
    assert consent is not None
    assert consent["governance"]["execution_authorized"] is False
    assert consents is not None and len(consents["consents"]) == 1


@pytest.mark.parametrize(
    "name",
    [
        "p2p_sync_status",
        "p2p_project_remote_show",
        "p2p_proposal_branch",
        "p2p_proposal_draft_commit",
        "p2p_work_branch",
    ],
)
def test_removed_collaboration_tools_are_unreachable(
    tmp_path: Path,
    name: str,
) -> None:
    _workspace(tmp_path)

    with pytest.raises(ValueError, match="Unknown MCP tool"):
        call_tool(name, {"root": str(tmp_path)})
