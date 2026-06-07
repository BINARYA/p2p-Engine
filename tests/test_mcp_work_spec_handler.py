from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.mcp.handlers.work_specs import handle_work_spec_tool
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace

runner = CliRunner()


def _setup_project(tmp_path: Path) -> P2PWorkspace:
    call_tool("p2p_init_project", {"root": str(tmp_path), "name": "Demo Project", "domain": "software"})
    call_tool(
        "p2p_proposal_create",
        {
            "root": str(tmp_path),
            "title": "Work Spec Proposal",
            "problem": "Need work spec handler coverage.",
            "proposal": "Route spec and work tools outside the facade.",
            "acceptance_criteria": ["Spec export can be generated."],
        },
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    return P2PWorkspace(tmp_path)


def test_mcp_work_spec_handler_returns_none_for_other_domains(tmp_path: Path) -> None:
    workspace = _setup_project(tmp_path)

    assert handle_work_spec_tool(workspace, "p2p_context", {}) is None


def test_mcp_work_spec_handler_serves_prompts(tmp_path: Path) -> None:
    workspace = _setup_project(tmp_path)

    prompt = handle_work_spec_tool(workspace, "p2p_explore_prompt", {"proposal_id": "PROP-001"})
    spec_prompt = handle_work_spec_tool(workspace, "p2p_spec_prompt", {"change_id": "CHANGE-001"})

    assert prompt is not None
    assert prompt["explore_prompt"]["path"] == ".p2p/prompts/PROP-001/explore.prompt.md"
    assert spec_prompt is not None
    assert spec_prompt["spec_prompt"]["prompt_path"] == (
        ".p2p/outputs/software-spec/CHANGE-001/spec-refine.prompt.md"
    )


def test_mcp_work_spec_handler_serves_spec_export_and_work_flow(tmp_path: Path) -> None:
    workspace = _setup_project(tmp_path)

    spec = handle_work_spec_tool(workspace, "p2p_spec_refresh", {"change_id": "CHANGE-001"})
    export = handle_work_spec_tool(workspace, "p2p_spec_export", {"change_id": "CHANGE-001", "target": "generic"})
    validation = handle_work_spec_tool(
        workspace,
        "p2p_spec_export_validate",
        {"change_id": "CHANGE-001", "target": "generic"},
    )
    work = handle_work_spec_tool(workspace, "p2p_work_plan", {"change_id": "CHANGE-001", "target": "generic"})
    work_show = handle_work_spec_tool(workspace, "p2p_work_show", {"work_id": "WORK-001"})

    assert spec is not None
    assert spec["spec"]["status"] == "generated"
    assert export is not None
    assert export["export"]["status"] == "exported"
    assert validation is not None
    assert validation["validation"]["target"] == "generic"
    assert work is not None
    assert work["work"]["work_id"] == "WORK-001"
    assert work_show is not None
    assert work_show["work"]["change_id"] == "CHANGE-001"


def test_mcp_call_tool_uses_work_spec_handler(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    result = call_tool("p2p_change_show", {"root": str(tmp_path), "change_id": "CHANGE-001"})

    assert result["change"]["change_id"] == "CHANGE-001"
