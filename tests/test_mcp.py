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

    assert "p2p_project_status" in names
    assert "p2p_next" in names
    assert "p2p_proposal_show" in names
    assert not any("accept" in name or "decide" in name or "cleanup" in name for name in names)


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
