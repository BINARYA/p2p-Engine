from __future__ import annotations

import subprocess
from pathlib import Path

from p2p_engine.mcp.handlers.collaboration import handle_collaboration_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _workspace(tmp_path: Path) -> P2PWorkspace:
    call_tool(
        "p2p_init_project",
        {"root": str(tmp_path), "name": "Demo Project", "starter": "generic"},
    )
    call_tool(
        "p2p_proposal_create",
        {
            "root": str(tmp_path),
            "title": "Collaboration Proposal",
            "problem": "Need collaboration handler coverage.",
            "proposal": "Route collaboration tools outside the facade.",
        },
    )
    return P2PWorkspace(tmp_path)


def test_mcp_collaboration_handler_returns_none_for_other_domains(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    assert handle_collaboration_tool(workspace, "p2p_context", {}) is None


def test_mcp_collaboration_handler_serves_remote_consent_and_sync_status(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    remote = handle_collaboration_tool(workspace, "p2p_project_remote_show", {})
    consent = handle_collaboration_tool(
        workspace,
        "p2p_consent_request",
        {
            "operation": "sync_push",
            "target": "origin:main",
            "actor_id": "owner",
        },
    )
    consents = handle_collaboration_tool(workspace, "p2p_consent_status", {})
    sync = handle_collaboration_tool(workspace, "p2p_sync_status", {})

    assert remote is not None
    assert "remote" in remote
    assert consent is not None
    assert consent["governance"]["execution_authorized"] is False
    assert consents is not None
    assert len(consents["consents"]) == 1
    assert sync is not None
    assert "sync" in sync


def test_mcp_collaboration_handler_serves_branch_lifecycle_basics(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    call_tool(
        "p2p_proposal_update",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "problem": "Updated from MCP and still uncommitted.",
        },
    )

    committed = handle_collaboration_tool(
        workspace,
        "p2p_proposal_draft_commit",
        {"proposal_id": "PROP-001", "actor": "agent"},
    )
    branched = handle_collaboration_tool(
        workspace,
        "p2p_proposal_branch",
        {"proposal_id": "PROP-001", "actor": "agent"},
    )
    status = handle_collaboration_tool(
        workspace,
        "p2p_proposal_branch_status",
        {"proposal_id": "PROP-001"},
    )

    assert committed is not None
    assert committed["governance"]["published"] is False
    assert branched is not None
    assert branched["governance"]["merge_performed"] is False
    assert status is not None
    assert status["proposal_branch"]["proposal_id"] == "PROP-001"


def test_mcp_call_tool_uses_collaboration_handler(tmp_path: Path) -> None:
    _workspace(tmp_path)

    result = call_tool("p2p_project_remote_show", {"root": str(tmp_path)})

    assert "remote" in result
