from __future__ import annotations

from pathlib import Path

from p2p_engine.mcp.handlers.proposals import handle_proposal_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(tmp_path: Path) -> P2PWorkspace:
    call_tool("p2p_init_project", {"root": str(tmp_path), "name": "Demo Project"})
    return P2PWorkspace(tmp_path)


def test_mcp_proposal_handler_returns_none_for_other_domains(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    assert handle_proposal_tool(workspace, "p2p_context", {}) is None


def test_mcp_proposal_handler_creates_and_reads_proposal(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    created = handle_proposal_tool(
        workspace,
        "p2p_proposal_create",
        {
            "title": "MCP Proposal",
            "problem": "Need proposal handler coverage.",
            "proposal": "Handle proposal tools outside the facade.",
            "acceptance_criteria": ["Proposal can be shown."],
        },
    )
    shown = handle_proposal_tool(workspace, "p2p_proposal_show", {"proposal_id": "PROP-001"})

    assert created is not None
    assert created["governance"]["owner_decision_required"] is True
    assert shown is not None
    assert shown["proposal"]["proposal_id"] == "PROP-001"


def test_mcp_proposal_handler_serves_readiness_and_contributions(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    handle_proposal_tool(
        workspace,
        "p2p_proposal_create",
        {
            "title": "MCP Proposal",
            "problem": "Need proposal handler coverage.",
            "proposal": "Handle proposal tools outside the facade.",
            "acceptance_criteria": ["Readiness can be checked."],
        },
    )

    readiness = handle_proposal_tool(workspace, "p2p_proposal_readiness_get", {"proposal_id": "PROP-001"})
    contribution = handle_proposal_tool(
        workspace,
        "p2p_proposal_contribution_add",
        {
            "proposal_id": "PROP-001",
            "type": "suggestion",
            "text": "Keep compatibility surface stable.",
        },
    )
    contributions = handle_proposal_tool(
        workspace,
        "p2p_proposal_contribution_list",
        {"proposal_id": "PROP-001"},
    )

    assert readiness is not None
    assert readiness["readiness"]["proposal_id"] == "PROP-001"
    assert contribution is not None
    assert contribution["governance"]["decision_made"] is False
    assert contributions is not None
    assert len(contributions["contributions"]["contributions"]) == 1


def test_mcp_call_tool_uses_proposal_handler(tmp_path: Path) -> None:
    _workspace(tmp_path)

    result = call_tool(
        "p2p_proposal_create",
        {
            "root": str(tmp_path),
            "title": "Facade Routed Proposal",
            "problem": "Need facade routing coverage.",
            "proposal": "Route through proposal handler.",
        },
    )

    assert result["proposal"]["proposal_id"] == "PROP-001"
