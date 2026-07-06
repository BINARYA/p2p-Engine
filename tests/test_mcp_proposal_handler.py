from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.mcp.handlers.proposals import handle_proposal_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(tmp_path: Path) -> P2PWorkspace:
    call_tool("p2p_init_project", {"root": str(tmp_path), "name": "Demo Project"})
    return P2PWorkspace(tmp_path)


def _proposal(workspace: P2PWorkspace) -> None:
    handle_proposal_tool(
        workspace,
        "p2p_proposal_create",
        {
            "title": "Artifact Import MCP",
            "proposal": "Import generated artifacts through MCP.",
        },
    )


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


def test_mcp_proposal_handler_serves_artifact_state_tools(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    handle_proposal_tool(
        workspace,
        "p2p_proposal_create",
        {
            "title": "Artifact MCP",
            "proposal": "This proposal changes MCP and CLI behavior.",
        },
    )

    status = handle_proposal_tool(workspace, "p2p_proposal_artifact_status", {"proposal_id": "PROP-001"})
    update = handle_proposal_tool(
        workspace,
        "p2p_proposal_artifact_set",
        {
            "proposal_id": "PROP-001",
            "artifact_id": "impact_map",
            "status": "not_applicable",
            "reason": "No external impact.",
            "actor": "codex",
        },
    )
    confirm = handle_proposal_tool(
        workspace,
        "p2p_proposal_artifact_confirm",
        {"proposal_id": "PROP-001", "artifact_id": "impact_map", "actor": "owner"},
    )

    assert status is not None
    assert status["artifact_state"]["status"] == "active"
    assert update is not None
    assert update["governance"]["decision_made"] is False
    assert update["artifact_operation"]["artifact"]["confirmation"] == "agent_proposed"
    assert confirm is not None
    assert confirm["artifact_operation"]["artifact"]["confirmation"] == "owner_confirmed"


def test_mcp_proposal_handler_imports_artifact_content_from_source_paths(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _proposal(workspace)
    sources = {
        "p2p_explore_import": ("explore.md", "# Exploration\n\nMCP source.\n", "exploration.md"),
        "p2p_impact_import": ("impact.yml", "impact: []\n", "impact-map.yml"),
        "p2p_clarify_import": ("clarify.md", "# Clarify\n\nMCP source.\n", "clarifications.md"),
        "p2p_synthesize_import": ("proposal.md", "# Proposal\n\nMCP source.\n", "proposal.md"),
        "p2p_plan_import": ("plan.md", "# Plan\n\nMCP source.\n", "execution-plan.md"),
        "p2p_tasks_import": ("tasks.yml", "tasks: []\n", "tasks.yml"),
    }

    for tool, (filename, content, target) in sources.items():
        source = tmp_path / filename
        source.write_text(content, encoding="utf-8")
        source_arg = filename if tool == "p2p_plan_import" else str(source)
        result = handle_proposal_tool(workspace, tool, {"proposal_id": "PROP-001", "source": source_arg})

        assert result is not None
        assert result["artifact_import"]["kind"] == tool.removeprefix("p2p_").removesuffix("_import")
        assert result["artifact_import"]["input_mode"] == "source"
        assert result["artifact_import"]["imported"][0]["filename"] == target
        assert result["governance"]["decision_made"] is False
        assert (tmp_path / ".p2p" / "proposals" / "PROP-001-artifact-import-mcp" / target).exists()


def test_mcp_proposal_handler_imports_direct_content_payloads(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _proposal(workspace)

    result = handle_proposal_tool(
        workspace,
        "p2p_tasks_import",
        {"proposal_id": "PROP-001", "content": "tasks: []\n"},
    )
    impact = handle_proposal_tool(
        workspace,
        "p2p_impact_import",
        {"proposal_id": "PROP-001", "content": "impact: []\n"},
    )

    assert result is not None
    assert result["artifact_import"]["input_mode"] == "content"
    assert result["artifact_import"]["imported"][0]["path"].endswith("/tasks.yml")
    assert result["artifact_import"]["imported"][0]["validated"] is True
    assert impact is not None
    assert impact["artifact_import"]["imported"][0]["filename"] == "impact-map.yml"
    assert impact["artifact_import"]["artifact_state_updated"] is False


def test_mcp_proposal_handler_imports_direct_artifact_payloads(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _proposal(workspace)

    exploration = handle_proposal_tool(
        workspace,
        "p2p_explore_import",
        {
            "proposal_id": "PROP-001",
            "artifacts": {
                "findings.md": "# Findings\n\nMCP finding.\n",
                "risks.md": "# Risks\n\nMCP risk.\n",
            },
        },
    )
    impact = handle_proposal_tool(
        workspace,
        "p2p_impact_import",
        {
            "proposal_id": "PROP-001",
            "artifacts": {
                "impact-map.yml": "impact: []\n",
                "conflict-analysis.yml": "conflicts: []\n",
            },
        },
    )

    assert exploration is not None
    assert [item["filename"] for item in exploration["artifact_import"]["imported"]] == ["findings.md", "risks.md"]
    assert impact is not None
    assert [item["filename"] for item in impact["artifact_import"]["imported"]] == [
        "impact-map.yml",
        "conflict-analysis.yml",
    ]
    assert all(item["validated"] is True for item in impact["artifact_import"]["imported"])


def test_mcp_proposal_handler_rejects_invalid_artifact_import_requests(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _proposal(workspace)

    with pytest.raises(ValueError, match="Provide exactly one"):
        handle_proposal_tool(workspace, "p2p_explore_import", {"proposal_id": "PROP-001"})
    with pytest.raises(ValueError, match="Provide exactly one"):
        handle_proposal_tool(
            workspace,
            "p2p_explore_import",
            {"proposal_id": "PROP-001", "source": "missing.md", "content": "# Duplicate\n"},
        )
    with pytest.raises(ValueError, match="Unsupported explore artifact filename"):
        handle_proposal_tool(
            workspace,
            "p2p_explore_import",
            {"proposal_id": "PROP-001", "artifacts": {"proposal.md": "# Wrong\n"}},
        )
    with pytest.raises(ValueError, match="Expected object argument: artifacts"):
        handle_proposal_tool(
            workspace,
            "p2p_explore_import",
            {"proposal_id": "PROP-001", "artifacts": ["findings.md"]},
        )
    with pytest.raises(ValueError, match="Invalid tasks YAML"):
        handle_proposal_tool(
            workspace,
            "p2p_tasks_import",
            {"proposal_id": "PROP-001", "content": "not_tasks: []\n"},
        )


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
