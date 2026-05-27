from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.mcp.server import handle_message
from p2p_engine.mcp.tools import call_tool, tool_definitions

runner = CliRunner()


def _setup_project(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "MCP Demo",
            "--problem",
            "Need structured agent access.",
            "--proposal",
            "Expose read-only MCP tools.",
            "--acceptance",
            "MCP tools can read project state.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])


def test_mcp_tool_definitions_are_read_only() -> None:
    names = {tool["name"] for tool in tool_definitions()}

    assert "p2p_init_project" in names
    assert "p2p_agent_instructions_refresh" in names
    assert "p2p_registry_refresh" in names
    assert "p2p_project_status" in names
    assert "p2p_next" in names
    assert "p2p_proposal_show" in names
    assert not any("accept" in name or "decide" in name or "cleanup" in name for name in names)


def test_mcp_write_safe_bootstrap_tools(tmp_path: Path) -> None:
    initialized = call_tool(
        "p2p_init_project",
        {
            "root": str(tmp_path),
            "name": "MCP Bootstrap",
            "agent": "codex",
            "repository": "cloud",
        },
    )

    assert initialized["initialized"] is True
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".p2p" / "agent-policy.yml").exists()
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()

    refreshed = call_tool(
        "p2p_agent_instructions_refresh",
        {"root": str(tmp_path), "profile": "claude"},
    )

    assert refreshed["agent_instructions"]["profile"] == "claude"
    assert (tmp_path / "CLAUDE.md").exists()
    policy = (tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8")
    assert "- codex" in policy
    assert "- claude" in policy


def test_mcp_registry_refresh_tool(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = call_tool("p2p_registry_refresh", {"root": str(tmp_path)})

    written = result["written"]
    assert ".p2p/registries/proposals.yml" in written
    assert (tmp_path / ".p2p" / "registries" / "proposals.yml").exists()


def test_mcp_call_tool_reads_project_state(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    result = call_tool("p2p_project_status", {"root": str(tmp_path)})

    assert result["project_status"]["accepted_proposals"] == 1
    assert result["project_status"]["operational_brief_available"] is False


def test_mcp_jsonrpc_lists_and_calls_tools(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    initialize = handle_message(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        default_root=tmp_path,
    )
    assert initialize is not None
    assert initialize["result"]["serverInfo"]["name"] == "p2p-engine"

    listed = handle_message(
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
        default_root=tmp_path,
    )
    assert listed is not None
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert "p2p_proposal_list" in names

    called = handle_message(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "p2p_proposal_show", "arguments": {"proposal_id": "PROP-001"}},
            }
        ),
        default_root=tmp_path,
    )
    assert called is not None
    content = called["result"]["content"][0]["text"]
    payload = json.loads(content)
    assert payload["proposal"]["proposal_id"] == "PROP-001"
    assert payload["proposal"]["title"] == "MCP Demo"
