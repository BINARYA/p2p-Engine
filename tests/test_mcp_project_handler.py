from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.mcp.handlers.project import handle_project_tool
from p2p_engine.mcp.registry import tool_definitions
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.filesystem_assertions import assert_no_workspace_mutation


runner = CliRunner()


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


def test_mcp_workspace_schema_and_plan_are_read_only(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema_path.unlink()
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    schema = call_tool("p2p_workspace_schema_status", {"root": str(tmp_path)})
    plan = call_tool(
        "p2p_workspace_migration_plan",
        {"root": str(tmp_path), "target_version": 1, "owner_inputs": {}},
    )

    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert schema["workspace_schema"] == workspace.workspace_schema_status().to_dict()
    assert plan["migration_plan"] == workspace.workspace_migration_plan(1, {}).to_dict()
    assert schema["mutation_performed"] is False
    assert plan["mutation_performed"] is False
    assert before == after
    assert "p2p_workspace_migration_apply" not in {
        definition["name"] for definition in tool_definitions()
    }
    assert {
        "p2p_workspace_migration_apply",
        "p2p_workspace_migration_rollback",
        "p2p_workspace_migration_resume",
    }.isdisjoint({definition["name"] for definition in tool_definitions()})


def test_mcp_progress_freshness_and_coverage_reads_are_mutation_free(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "MCP read parity",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal = workspace.create_proposal_with_details(
        "Data model evidence",
        problem="Domain entities and lifecycle are missing.",
        proposal="Define data entities and state lifecycle.",
    )
    with assert_no_workspace_mutation(tmp_path):
        progress = call_tool("p2p_project_progress", {"root": str(tmp_path)})
        freshness = call_tool("p2p_project_freshness", {"root": str(tmp_path)})
        coverage = call_tool(
            "p2p_proposal_vertical_coverage_show",
            {"root": str(tmp_path), "proposal_id": proposal.proposal_id},
        )
        suggestion = call_tool(
            "p2p_proposal_vertical_coverage_suggest",
            {"root": str(tmp_path), "proposal_id": proposal.proposal_id},
        )

    assert progress["project_progress"]["definition"]["status"] == "measured"
    assert progress["mutation_performed"] is False
    assert freshness["project_freshness"]["graph_version"] == 1
    assert freshness["mutation_performed"] is False
    assert coverage["vertical_coverage"]["state"] == "absent_legacy"
    assert coverage["mutation_performed"] is False
    assert suggestion["vertical_coverage_suggestion"]["candidates"]
    assert suggestion["mutation_performed"] is False


def test_mcp_project_readiness_reads_are_bounded_and_expose_no_write_tools(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("MCP readiness", owner="owner", vertical_id="base_project")
    question = workspace.next_project_question()
    assert question is not None

    with assert_no_workspace_mutation(tmp_path):
        review = call_tool(
            "p2p_project_readiness_review",
            {"root": str(tmp_path), "limit": 2},
        )
        gaps = call_tool(
            "p2p_project_readiness_gaps",
            {"root": str(tmp_path), "limit": 2},
        )
        questions = call_tool(
            "p2p_project_questions_status",
            {"root": str(tmp_path), "limit": 2},
        )
        next_question = call_tool(
            "p2p_project_questions_next",
            {"root": str(tmp_path)},
        )

    assert review["mutation_performed"] is False
    assert review["gaps"]["limit"] == 2
    assert gaps["project_readiness_page"]["limit"] == 2
    assert questions["project_questions"]["limit"] == 2
    assert next_question["project_question"]["question_id"] == question.question_id
    names = {item["name"] for item in tool_definitions()}
    assert {
        "p2p_project_questions_answer",
        "p2p_project_questions_defer",
        "p2p_project_questions_mute",
        "p2p_project_questions_reopen",
        "p2p_project_readiness_apply",
    }.isdisjoint(names)


def test_cli_and_mcp_project_readiness_share_stable_semantic_fields(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Readiness parity", owner="owner", vertical_id="base_project")

    cli = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "gaps",
            "--limit",
            "2",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    mcp = call_tool(
        "p2p_project_readiness_gaps",
        {"root": str(tmp_path), "limit": 2},
    )

    assert cli.exit_code == 0
    cli_page = json.loads(cli.output)["project_readiness_page"]
    mcp_page = mcp["project_readiness_page"]
    assert cli_page["total"] == mcp_page["total"]
    assert cli_page["snapshot_fingerprint"] == mcp_page["snapshot_fingerprint"]
    assert [item["gap_id"] for item in cli_page["items"]] == [
        item["gap_id"] for item in mcp_page["items"]
    ]
