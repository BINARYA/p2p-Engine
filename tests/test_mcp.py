from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine import __version__
from p2p_engine.cli import app
from p2p_engine.core.contribution import allowed_contribution_type_values
from p2p_engine.mcp.server import handle_message
from p2p_engine.mcp.handlers.common import to_jsonable
from p2p_engine.mcp.tools import TOOL_NAMES, call_tool, tool_definitions
from p2p_engine.storage.filesystem import P2PWorkspace

runner = CliRunner()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


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


def _setup_work_lifecycle_project(tmp_path: Path) -> Path:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "MCP Work Demo",
            "--problem",
            "Need Work lifecycle MCP parity.",
            "--proposal",
            "Expose Work lifecycle tools through local MCP.",
            "--acceptance",
            "Work lifecycle tools are callable through MCP.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    call_tool("p2p_spec_refresh", {"root": str(tmp_path), "change_id": "CHANGE-001"})
    call_tool("p2p_spec_export", {"root": str(tmp_path), "change_id": "CHANGE-001", "target": "generic"})
    call_tool("p2p_work_plan", {"root": str(tmp_path), "change_id": "CHANGE-001", "target": "generic"})
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    for operation in (
        "work_publish",
        "work_request_review",
        "work_accept",
        "work_finalize",
        "work_cleanup",
    ):
        runner.invoke(
            app,
            [
                "consent",
                "grant",
                operation,
                "WORK-001",
                "--actor",
                "lorenzo",
                "--approved-by",
                "matteo",
                "--root",
                str(tmp_path),
            ],
        )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline with work lifecycle consents")
    _git(tmp_path, "branch", "-M", "main")
    return remote_path


def test_mcp_tool_definitions_expose_agent_safe_surface() -> None:
    names = {tool["name"] for tool in tool_definitions()}
    proposal_show = next(tool for tool in tool_definitions() if tool["name"] == "p2p_proposal_show")

    assert set(TOOL_NAMES) == names
    assert proposal_show["inputSchema"]["properties"]["full"]["type"] == "boolean"

    expected = {
        "p2p_init_project",
        "p2p_agent_instructions_refresh",
        "p2p_agent_list",
        "p2p_agent_show",
        "p2p_agent_doctor",
        "p2p_agent_install",
        "p2p_agent_update",
        "p2p_agent_uninstall",
        "p2p_registry_refresh",
        "p2p_validate",
        "p2p_context",
        "p2p_assess_refresh",
        "p2p_assess_show",
        "p2p_project_rubrics_init",
        "p2p_project_rubrics_show",
        "p2p_maturity_refresh",
        "p2p_maturity_show",
        "p2p_proposal_create",
        "p2p_proposal_update",
        "p2p_proposal_contribution_add",
        "p2p_proposal_contribution_list",
        "p2p_intake_prompt",
        "p2p_intake_status",
        "p2p_project_brief_prompt",
        "p2p_project_brief_show",
        "p2p_choice_discover",
        "p2p_conflict_status",
        "p2p_governance_status",
        "p2p_governance_validate",
        "p2p_choice_governance_preflight",
        "p2p_vote_status",
        "p2p_precedent_search",
        "p2p_impact_prompt",
        "p2p_explore_import",
        "p2p_impact_import",
        "p2p_clarify_import",
        "p2p_synthesize_import",
        "p2p_plan_import",
        "p2p_tasks_import",
        "p2p_project_status",
        "p2p_project_interaction_style_show",
        "p2p_project_interaction_style_set",
        "p2p_next",
        "p2p_next_add",
        "p2p_next_complete",
        "p2p_next_retire",
        "p2p_next_refresh",
        "p2p_proposal_list",
        "p2p_proposal_show",
        "p2p_proposal_readiness_get",
        "p2p_proposal_readiness_init",
        "p2p_proposal_readiness_refresh",
        "p2p_proposal_readiness_assess",
        "p2p_proposal_readiness_explain",
        "p2p_proposal_readiness_list_gaps",
        "p2p_proposal_readiness_review",
        "p2p_proposal_questions_status",
        "p2p_proposal_questions_init",
        "p2p_proposal_questions_add",
        "p2p_proposal_questions_answer",
        "p2p_proposal_questions_next",
        "p2p_proposal_questions_apply",
        "p2p_choice_list",
        "p2p_choice_show",
        "p2p_change_status",
        "p2p_change_show",
        "p2p_change_tasks",
        "p2p_work_list",
        "p2p_work_status",
        "p2p_work_show",
        "p2p_work_branch",
        "p2p_work_submit",
        "p2p_work_review",
        "p2p_registry_status",
        "p2p_registry_show",
        "p2p_project_show",
        "p2p_project_export",
        "p2p_project_export_status",
        "p2p_project_publish_prepare",
        "p2p_project_publish_import",
        "p2p_project_publish_validate",
        "p2p_project_publish_render",
        "p2p_project_publish_status",
        "p2p_project_vertical_list",
        "p2p_project_vertical_show",
        "p2p_project_vertical_validate",
        "p2p_project_vertical_propose",
        "p2p_project_vertical_add",
        "p2p_project_vertical_select",
        "p2p_project_vertical_lock_show",
        "p2p_project_vertical_lock_repair",
        "p2p_project_context",
        "p2p_project_sections",
        "p2p_project_section_show",
        "p2p_project_definition_show",
        "p2p_project_definition_update",
        "p2p_project_readiness_review",
        "p2p_project_remote_show",
        "p2p_project_remote_configure",
        "p2p_permissions_show",
        "p2p_consent_request",
        "p2p_consent_status",
        "p2p_consent_show",
        "p2p_sync_status",
        "p2p_sync_fetch",
        "p2p_sync_pull",
        "p2p_sync_push",
        "p2p_proposal_draft_commit",
        "p2p_proposal_branch",
        "p2p_proposal_branch_status",
        "p2p_proposal_publish",
        "p2p_proposal_request_review",
        "p2p_proposal_accept",
        "p2p_proposal_reject",
        "p2p_proposal_defer",
        "p2p_proposal_accept_branch",
        "p2p_proposal_reject_branch",
        "p2p_proposal_merge",
        "p2p_proposal_finalize",
        "p2p_proposal_cleanup",
        "p2p_proposal_branch_scan",
        "p2p_spec_lifecycle",
        "p2p_spec_status",
        "p2p_spec_show",
        "p2p_spec_export_status",
        "p2p_spec_export_show",
        "p2p_change_create",
        "p2p_project_refresh",
        "p2p_spec_refresh",
        "p2p_spec_export",
        "p2p_spec_export_validate",
        "p2p_work_plan",
        "p2p_work_publish",
        "p2p_work_request_review",
        "p2p_work_accept",
        "p2p_work_finalize",
        "p2p_work_cleanup",
        "p2p_explore_prompt",
        "p2p_digest_prompt",
        "p2p_clarify_prompt",
        "p2p_synthesize_prompt",
        "p2p_plan_prompt",
        "p2p_tasks_prompt",
        "p2p_swot_prompt",
        "p2p_spec_prompt",
    }

    assert expected <= names
    allowed_decision_tools = {
        "p2p_proposal_accept",
        "p2p_proposal_reject",
        "p2p_proposal_defer",
        "p2p_proposal_accept_branch",
        "p2p_proposal_reject_branch",
        "p2p_work_accept",
    }
    allowed_cleanup_tools = {"p2p_proposal_cleanup", "p2p_work_cleanup"}
    allowed_merge_tools = {"p2p_proposal_merge", "p2p_work_accept"}
    assert not any(
        ("accept" in name and name not in allowed_decision_tools)
        or ("reject" in name and name not in allowed_decision_tools)
        or ("defer" in name and name not in allowed_decision_tools)
        or "decide" in name
        or ("cleanup" in name and name not in allowed_cleanup_tools)
        or (("merge" in name) and name not in allowed_merge_tools)
        or "contribution_accept" in name
        or "record_conflict" in name
        or "block" in name
        or "retire_branch" in name
        or "consent_grant" in name
        or "consent_revoke" in name
        for name in names
    )


def test_mcp_proposal_contribution_schema_matches_core_types() -> None:
    contribution_tool = next(
        tool for tool in tool_definitions() if tool["name"] == "p2p_proposal_contribution_add"
    )

    schema_types = contribution_tool["inputSchema"]["properties"]["type"]["enum"]

    assert tuple(schema_types) == allowed_contribution_type_values()


def test_mcp_governance_policy_read_only_tools(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Vote Target", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Deployment Strategy",
            "--option",
            "Blue",
            "--option",
            "Green",
            "--related",
            "PROP-001",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "vote",
            "record",
            "PROP-001",
            "--choice",
            "A",
            "--reason",
            "Prefer blue.",
            "--voter",
            "owner",
            "--role",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )
    precedent_path = tmp_path / ".p2p" / "governance" / "decision-precedents.yml"
    precedent_path.parent.mkdir(parents=True, exist_ok=True)
    precedent_path.write_text(
        yaml.safe_dump({"precedents": [{"id": "DP001", "related_choices": ["CHOICE-001"], "tags": ["deployment"]}]}),
        encoding="utf-8",
    )
    before = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / ".p2p").rglob("*"))
        if path.is_file()
    }

    status = call_tool("p2p_governance_status", {"root": str(tmp_path)})
    validation = call_tool("p2p_governance_validate", {"root": str(tmp_path)})
    preflight = call_tool(
        "p2p_choice_governance_preflight",
        {"root": str(tmp_path), "choice_id": "CHOICE-001", "option": "B", "actor": "owner"},
    )
    vote = call_tool("p2p_vote_status", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    precedents = call_tool("p2p_precedent_search", {"root": str(tmp_path), "choice_id": "CHOICE-001"})

    assert status["mutation_performed"] is False
    assert validation["governance_validation"]["ok"] is True
    assert preflight["mutation_performed"] is False
    assert preflight["decision_made"] is False
    assert preflight["governance_preflight"]["schema_version"] == "governance-preflight/v1"
    assert preflight["governance_preflight"]["vote_summary"]["alignment"] == "conflicts"
    assert "P2P_GOV_RELATED_PRECEDENTS" in [
        warning["code"] for warning in preflight["governance_preflight"]["warnings"]
    ]
    assert vote["vote_status"]["winner"] == "A"
    assert precedents["precedents"][0]["precedent_id"] == "DP001"
    assert "p2p_vote_record" not in TOOL_NAMES
    assert "p2p_precedent_record" not in TOOL_NAMES
    assert "p2p_choice_decide" not in TOOL_NAMES
    after = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / ".p2p").rglob("*"))
        if path.is_file()
    }
    assert after == before


def test_mcp_governance_preflight_reports_malformed_precedents(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Deployment Strategy",
            "--option",
            "Blue",
            "--option",
            "Green",
            "--root",
            str(tmp_path),
        ],
    )
    precedent_path = tmp_path / ".p2p" / "governance" / "decision-precedents.yml"
    precedent_path.parent.mkdir(parents=True, exist_ok=True)
    precedent_path.write_text("precedents: {}\n", encoding="utf-8")

    result = call_tool(
        "p2p_choice_governance_preflight",
        {"root": str(tmp_path), "choice_id": "CHOICE-001", "option": "A", "actor": "owner"},
    )

    preflight = result["governance_preflight"]
    assert result["mutation_performed"] is False
    assert preflight["result"]["status"] == "blocked"
    assert [error["code"] for error in preflight["blocking_errors"]] == ["P2P_GOV_MALFORMED_PRECEDENTS"]
    assert preflight["precedents"] == []


def test_mcp_project_visible_export_flow(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Visible Project Output",
            "--problem",
            "Project definitions are hard to inspect.",
            "--proposal",
            "Export a visible chaptered project definition.",
            "--acceptance",
            "outputs/latest/project.md exists.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])

    exported = call_tool("p2p_project_export", {"root": str(tmp_path)})

    assert exported["export"]["status"] == "exported"
    assert exported["export"]["latest_path"] == "outputs/latest/project.md"
    assert (tmp_path / "outputs" / "latest" / "project.md").exists()

    status = call_tool("p2p_project_export_status", {"root": str(tmp_path)})
    assert status["export_status"]["latest_exists"] is True
    assert status["export_status"]["latest_path"] == "outputs/latest/project.md"


def test_mcp_project_publish_prepare_import_and_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "MCP Project Publication", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Canonical Project Publication",
            "--problem",
            "Generated project output is hard to read.",
            "--goal",
            "Prepare one canonical human project publication.",
            "--proposal",
            "Create a staged publication pipeline above outputs/latest/project.md.",
            "--acceptance",
            "A curated publication can be imported.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])

    prepared = call_tool("p2p_project_publish_prepare", {"root": str(tmp_path)})
    prepared_again = call_tool("p2p_project_publish_prepare", {"root": str(tmp_path)})

    assert prepared["publication_prepare"]["status"] == "prepared"
    assert prepared["publication_prepare"]["exported"] is True
    assert prepared_again["publication_prepare"]["exported"] is False
    assert not (tmp_path / "outputs" / "review-001").exists()

    draft = tmp_path / "curated-draft.md"
    draft.write_text(
        "# MCP Project Publication\n\n"
        "## Executive Summary\n\n"
        "The project has one canonical human publication.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    imported = call_tool(
        "p2p_project_publish_import",
        {"root": str(tmp_path), "source": str(draft)},
    )
    validation = call_tool("p2p_project_publish_validate", {"root": str(tmp_path)})
    status = call_tool("p2p_project_publish_status", {"root": str(tmp_path)})

    assert imported["publication_import"]["curated_path"] == "outputs/latest/project.curated.md"
    assert validation["publication_validation"]["status"] == "passed"
    stages = {stage["name"]: stage for stage in status["publication_status"]["stages"]}
    assert stages["curated"]["status"] == "ready"
    assert stages["validation"]["status"] == "ready"
    assert status["publication_status"]["validation_status"] == "passed"
    assert status["publication_status"]["approved_for_publication"] is False


def test_mcp_project_publish_render_with_fake_renderer(tmp_path: Path, monkeypatch) -> None:
    def fake_renderer(markdown_text: str, output_path: Path, root: Path) -> str:
        output_path.write_bytes(b"%PDF-1.4\n% fake mcp publication pdf\n")
        return "fake-mcp-renderer"

    monkeypatch.setattr("p2p_engine.services.project_publication.render_pdf_with_weasyprint", fake_renderer)
    runner.invoke(app, ["init", "MCP Project Publication", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Canonical Project Publication",
            "--problem",
            "Generated project output is hard to read.",
            "--goal",
            "Prepare one canonical human project publication.",
            "--proposal",
            "Create a staged publication pipeline above outputs/latest/project.md.",
            "--acceptance",
            "A curated publication can be imported.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    call_tool("p2p_project_publish_prepare", {"root": str(tmp_path)})
    draft = tmp_path / "curated-draft.md"
    draft.write_text(
        "# MCP Project Publication\n\n"
        "## Executive Summary\n\n"
        "The project has one canonical human publication for the current project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    call_tool("p2p_project_publish_import", {"root": str(tmp_path), "source": str(draft)})
    call_tool("p2p_project_publish_validate", {"root": str(tmp_path)})

    rendered = call_tool("p2p_project_publish_render", {"root": str(tmp_path)})
    status = call_tool("p2p_project_publish_status", {"root": str(tmp_path)})

    assert rendered["publication_render"]["status"] == "rendered"
    assert rendered["publication_render"]["renderer"] == "fake-mcp-renderer"
    assert status["publication_status"]["render_status"] == "rendered"
    assert "p2p_project_publish_review" not in TOOL_NAMES


def test_mcp_project_interaction_style_tools(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Interaction MCP Demo", "--root", str(tmp_path)])

    shown = call_tool("p2p_project_interaction_style_show", {"root": str(tmp_path)})
    assert shown["interaction_style"]["configured"] is False
    assert shown["interaction_style"]["technical_verbosity"]["value"] == 2
    assert shown["interaction_style"]["formality"]["value"] == 2
    assert shown["interaction_style"]["assertiveness"]["value"] == 0
    assert not (tmp_path / ".p2p" / "project" / "interaction-style.yml").exists()

    updated = call_tool(
        "p2p_project_interaction_style_set",
        {
            "root": str(tmp_path),
            "technical_verbosity": 5,
            "formality": 4,
            "actor": "mcp-client",
        },
    )
    assert updated["interaction_style"]["configured"] is True
    assert updated["interaction_style"]["technical_verbosity"]["value"] == 5
    assert updated["interaction_style"]["formality"]["value"] == 4
    assert updated["interaction_style"]["assertiveness"]["value"] == 0
    payload = yaml.safe_load((tmp_path / ".p2p" / "project" / "interaction-style.yml").read_text(encoding="utf-8"))
    assert payload["interaction_style"]["updated_by"] == "mcp-client"


def test_mcp_project_vertical_and_readiness_tools(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Vertical MCP Demo", "--root", str(tmp_path)])

    listed = call_tool("p2p_project_vertical_list", {"root": str(tmp_path)})
    ids = {item["vertical_id"] for item in listed["verticals"]}
    assert "base_project" in ids
    assert listed["active"]["fallback_used"] is True

    shown = call_tool(
        "p2p_project_vertical_show",
        {"root": str(tmp_path), "vertical_id": "social_impact_program_design"},
    )
    section_ids = {section["section_id"] for section in shown["vertical"]["sections"]}
    assert {"vision", "measurement_reporting"} <= section_ids

    validation = call_tool("p2p_project_vertical_validate", {"root": str(tmp_path), "target": "base_project"})
    assert validation["validation"]["valid"] is True

    candidate = call_tool(
        "p2p_project_vertical_propose",
        {"root": str(tmp_path), "idea": "progettare la scatola perfetta"},
    )
    assert candidate["candidate"]["pack"]["vertical_id"] == "packaging_or_physical_product_design"

    selected = call_tool(
        "p2p_project_vertical_select",
        {"root": str(tmp_path), "vertical_id": "social_impact_program_design", "actor": "owner"},
    )
    assert selected["active"]["vertical_id"] == "social_impact_program_design"

    review = call_tool("p2p_project_readiness_review", {"root": str(tmp_path)})
    assert review["readiness_review"]["active_vertical_id"] == "social_impact_program_design"
    assert review["readiness_review"]["missing_capisaldi"]

    lock = call_tool("p2p_project_vertical_lock_show", {"root": str(tmp_path)})
    assert lock["lock_status"]["status"] == "valid"

    context = call_tool("p2p_project_context", {"root": str(tmp_path)})
    assert context["project_context"]["active"]["vertical_id"] == "social_impact_program_design"
    assert context["project_context"]["lock_status"]["status"] == "valid"

    sections = call_tool("p2p_project_sections", {"root": str(tmp_path)})
    assert any(section["section_id"] == "measurement_reporting" for section in sections["sections"])

    section = call_tool(
        "p2p_project_section_show",
        {"root": str(tmp_path), "section_id": "measurement_reporting"},
    )
    assert section["section"]["section_id"] == "measurement_reporting"

    definition = call_tool("p2p_project_definition_show", {"root": str(tmp_path)})
    assert definition["definition"]["exists"] is True

    patch = tmp_path / "definition-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: set_field\n"
        "      section_id: measurement_reporting\n"
        "      field_id: summary\n"
        "      value: Outcome evidence and cadence.\n",
        encoding="utf-8",
    )
    updated = call_tool("p2p_project_definition_update", {"root": str(tmp_path), "patch": str(patch)})
    assert updated["definition_update"]["operations_applied"] == 1


def test_mcp_managed_next_action_lifecycle(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])

    added = call_tool(
        "p2p_next_add",
        {
            "root": str(tmp_path),
            "kind": "verify_integration",
            "target": "mcp-client",
            "priority": "high",
            "reason": "Verify real MCP client setup.",
            "command": "p2p-mcp-server --root /path/to/project",
        },
    )

    assert added["next_action"]["action_id"] == "NEXT-001"
    assert added["next_action"]["priority"] == "high"
    assert added["next_action"]["source"] == ".p2p/project/next-actions.yml"

    listed = call_tool("p2p_next", {"root": str(tmp_path)})
    assert listed["next_actions"][0]["action_id"] == "NEXT-001"
    assert listed["next_actions"][0]["kind"] == "verify_integration"

    completed = call_tool(
        "p2p_next_complete",
        {"root": str(tmp_path), "action_id": "NEXT-001", "reason": "Verified."},
    )

    assert completed["next_action_result"]["action"]["status"] == "completed"
    assert completed["next_action_result"]["path"] == ".p2p/project/next-actions-log.yml"
    active = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions.yml").read_text(encoding="utf-8"))
    assert active["next_actions"] == []
    log = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions-log.yml").read_text(encoding="utf-8"))
    assert log["next_action_log"][0]["id"] == "NEXT-001"
    assert log["next_action_log"][0]["status"] == "completed"


def test_mcp_next_retire_and_refresh(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--domain", "software", "--root", str(tmp_path)])
    call_tool(
        "p2p_next_add",
        {"root": str(tmp_path), "kind": "define_scope", "target": "temporary", "reason": "Temporary item."},
    )

    retired = call_tool(
        "p2p_next_retire",
        {"root": str(tmp_path), "action_id": "NEXT-001", "reason": "Superseded."},
    )

    assert retired["next_action_result"]["action"]["status"] == "retired"
    refreshed = call_tool("p2p_next_refresh", {"root": str(tmp_path)})
    assert refreshed["next_action_refresh"]["active_curated"] == 0
    assert refreshed["next_action_refresh"]["generated"] >= 1


def test_mcp_safe_managed_sync_and_proposal_branch_tools(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Branch Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "generic",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    sync_status = call_tool("p2p_sync_status", {"root": str(tmp_path)})
    assert sync_status["sync"]["can_sync"] is True
    assert sync_status["sync"]["remote"] == "origin"

    fetched = call_tool("p2p_sync_fetch", {"root": str(tmp_path)})
    assert fetched["sync"]["status"] == "fetched"

    branched = call_tool("p2p_proposal_branch", {"root": str(tmp_path), "proposal_id": "PROP-001", "actor": "agent"})

    branch = branched["proposal_branch"]
    assert branch["proposal_id"] == "PROP-001"
    assert branch["status"] == "branched"
    assert branch["branch_name"].startswith("p2p/proposal/PROP-001-mcp-branch-demo-agent-")
    assert branched["governance"]["merge_performed"] is False

    scanned = call_tool("p2p_proposal_branch_scan", {"root": str(tmp_path)})
    assert scanned["proposal_branch_scan"]["proposals"][0]["proposal_id"] == "PROP-001"

    status = call_tool("p2p_proposal_branch_status", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    assert status["proposal_branch"]["status"] == "branched"


def test_mcp_remote_configure_and_consent_request_are_write_safe(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))

    configured = call_tool(
        "p2p_project_remote_configure",
        {
            "root": str(tmp_path),
            "mode": "remote",
            "provider": "generic",
            "remote": "origin",
        },
    )

    assert configured["remote"]["mode"] == "remote"
    assert configured["remote"]["remote"] == "origin"
    assert configured["provider_side_effects"]["creates_remote_repository"] is False

    requested = call_tool(
        "p2p_consent_request",
        {
            "root": str(tmp_path),
            "operation": "proposal_publish",
            "target": "PROP-001",
            "actor_id": "lorenzo",
            "requested_by": "lorenzo",
        },
    )

    assert requested["consent"]["status"] == "requested"
    assert requested["governance"]["owner_decision_required"] is True
    assert requested["governance"]["execution_authorized"] is False
    receipt = yaml.safe_load((tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml").read_text(encoding="utf-8"))
    assert receipt["status"] == "requested"
    assert receipt["approved_by"] is None


def test_mcp_requested_consent_does_not_authorize_publish(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Requested Consent Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    call_tool("p2p_project_remote_configure", {"root": str(tmp_path), "mode": "remote", "provider": "generic"})
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    call_tool("p2p_proposal_branch", {"root": str(tmp_path), "proposal_id": "PROP-001", "actor": "lorenzo"})
    call_tool(
        "p2p_consent_request",
        {"root": str(tmp_path), "operation": "proposal_publish", "target": "PROP-001", "actor_id": "lorenzo"},
    )

    try:
        call_tool(
            "p2p_proposal_publish",
            {"root": str(tmp_path), "proposal_id": "PROP-001", "actor_id": "lorenzo", "consent_id": "CONSENT-001"},
        )
    except ValueError as exc:
        assert "Consent receipt is not granted" in str(exc)
    else:
        raise AssertionError("requested consent should not authorize publish")


def test_mcp_draft_proposal_decision_requires_granted_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Draft Reject Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    call_tool(
        "p2p_consent_request",
        {"root": str(tmp_path), "operation": "proposal_reject", "target": "PROP-001", "actor_id": "lorenzo"},
    )

    try:
        call_tool(
            "p2p_proposal_reject",
            {
                "root": str(tmp_path),
                "proposal_id": "PROP-001",
                "actor_id": "lorenzo",
                "consent_id": "CONSENT-001",
                "reason": "Out of scope.",
            },
        )
    except ValueError as exc:
        assert "Consent receipt is not granted" in str(exc)
    else:
        raise AssertionError("requested consent should not authorize draft proposal rejection")

    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_reject",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant draft proposal reject consent")

    rejected = call_tool(
        "p2p_proposal_reject",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-002",
            "reason": "Out of scope.",
        },
    )

    assert rejected["proposal_decision"]["outcome"] == "rejected"
    assert rejected["proposal_decision"]["approver"] == "lorenzo"
    assert rejected["governance"]["decision_made"] is True
    assert rejected["governance"]["decision_outcome"] == "rejected"
    assert rejected["consent"]["status"] == "consumed"
    proposal_text = next((tmp_path / ".p2p" / "proposals").glob("PROP-001-*/proposal.md")).read_text(encoding="utf-8")
    assert "## Status\n\n`rejected`" in proposal_text


def test_mcp_draft_proposal_accept_and_defer_consume_matching_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Draft Accept Demo", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Draft Defer Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    for operation, tool_name, proposal_id, expected in [
        ("proposal_accept", "p2p_proposal_accept", "PROP-001", "accepted"),
        ("proposal_defer", "p2p_proposal_defer", "PROP-002", "deferred"),
    ]:
        runner.invoke(
            app,
            [
                "consent",
                "grant",
                operation,
                proposal_id,
                "--actor",
                "lorenzo",
                "--approved-by",
                "matteo",
                "--root",
                str(tmp_path),
            ],
        )
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"grant {operation} consent")
        consent_id = f"CONSENT-00{1 if proposal_id == 'PROP-001' else 2}"
        result = call_tool(
            tool_name,
            {
                "root": str(tmp_path),
                "proposal_id": proposal_id,
                "actor_id": "lorenzo",
                "consent_id": consent_id,
                "reason": "Owner approved through consent.",
            },
        )

        assert result["proposal_decision"]["outcome"] == expected
        assert result["governance"]["decision_outcome"] == expected
        assert result["consent"]["status"] == "consumed"


def test_mcp_proposal_draft_commit_then_branch_from_explicit_base(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Commit Demo", "--root", str(tmp_path)])
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

    committed = call_tool("p2p_proposal_draft_commit", {"root": str(tmp_path), "proposal_id": "PROP-001", "actor": "agent"})

    assert committed["proposal_draft_commit"]["proposal_id"] == "PROP-001"
    assert any(
        "PROP-001-draft-commit-demo/proposal.md" in path
        for path in committed["proposal_draft_commit"]["changed_files"]
    )

    branched = call_tool(
        "p2p_proposal_branch",
        {"root": str(tmp_path), "proposal_id": "PROP-001", "actor": "agent", "base_branch": "main"},
    )

    assert branched["proposal_branch"]["base_branch"] == "main"
    assert _git(tmp_path, "branch", "--show-current").stdout.strip().startswith("p2p/proposal/PROP-001-")


def test_mcp_proposal_branch_refuses_proposal_branch_base_without_opt_in(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "First Branch", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Second Branch", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    call_tool("p2p_proposal_branch", {"root": str(tmp_path), "proposal_id": "PROP-001", "actor": "agent"})
    proposal_branch = _git(tmp_path, "branch", "--show-current").stdout.strip()

    try:
        call_tool(
            "p2p_proposal_branch",
            {
                "root": str(tmp_path),
                "proposal_id": "PROP-002",
                "actor": "agent",
                "base_branch": proposal_branch,
            },
        )
    except ValueError as exc:
        assert "Cannot create managed proposal branch from another proposal branch" in str(exc)
    else:
        raise AssertionError("proposal branch chaining should require explicit opt-in")


def test_mcp_proposal_publish_requires_and_consumes_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Publish Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(
        app,
        [
            "project",
            "remote",
            "configure",
            "--mode",
            "remote",
            "--provider",
            "generic",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    branch_name = _git(tmp_path, "branch", "--show-current").stdout.strip()
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_publish",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant proposal publish consent")

    result = call_tool(
        "p2p_proposal_publish",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-001",
        },
    )

    assert result["proposal_branch"]["status"] == "published"
    assert result["consent"]["status"] == "consumed"
    assert result["consent"]["operation"] == "proposal_publish"
    assert branch_name in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout
    receipt = yaml.safe_load((tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml").read_text(encoding="utf-8"))
    assert receipt["status"] == "consumed"
    assert receipt["result"]["branch"] == branch_name


def test_mcp_proposal_publish_rejects_actor_mismatch_without_consuming_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_publish",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )

    try:
        call_tool(
            "p2p_proposal_publish",
            {
                "root": str(tmp_path),
                "proposal_id": "PROP-001",
                "actor_id": "matteo",
                "consent_id": "CONSENT-001",
            },
        )
    except ValueError as exc:
        assert "Consent receipt actor mismatch" in str(exc)
    else:
        raise AssertionError("Expected actor mismatch to fail")

    receipt = yaml.safe_load((tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml").read_text(encoding="utf-8"))
    assert receipt["status"] == "granted"


def test_mcp_sync_push_requires_and_consumes_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "sync_push",
            "origin/main",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline with push consent")

    result = call_tool(
        "p2p_sync_push",
        {"root": str(tmp_path), "actor_id": "lorenzo", "consent_id": "CONSENT-001"},
    )

    assert result["sync"]["status"] == "pushed"
    assert result["consent"]["status"] == "consumed"
    assert "refs/heads/main" in _git(tmp_path, "ls-remote", "--heads", "origin", "main").stdout


def test_mcp_sync_pull_requires_and_consumes_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "sync_pull",
            "origin/main",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline with pull consent")
    _git(tmp_path, "push", "-u", "origin", "main")

    clone_path = tmp_path.parent / f"{tmp_path.name}-clone"
    subprocess.run(["git", "clone", "--branch", "main", str(remote_path), str(clone_path)], check=True, capture_output=True, text=True)
    _git(clone_path, "config", "user.email", "test@example.com")
    _git(clone_path, "config", "user.name", "Test User")
    (clone_path / "remote-change.txt").write_text("remote\n", encoding="utf-8")
    _git(clone_path, "add", ".")
    _git(clone_path, "commit", "-m", "remote change")
    _git(clone_path, "push", "origin", "main")

    result = call_tool(
        "p2p_sync_pull",
        {"root": str(tmp_path), "actor_id": "lorenzo", "consent_id": "CONSENT-001"},
    )

    assert result["sync"]["status"] == "pulled"
    assert result["consent"]["status"] == "consumed"
    assert (tmp_path / "remote-change.txt").read_text(encoding="utf-8") == "remote\n"


def test_mcp_proposal_request_review_requires_and_consumes_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Review Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_request_review",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant proposal review consent")

    result = call_tool(
        "p2p_proposal_request_review",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-001",
        },
    )

    assert result["proposal_branch"]["status"] == "review_requested"
    assert result["consent"]["status"] == "consumed"
    assert result["proposal_branch"]["metadata"]["review"]["provider"] == "generic"


def test_mcp_proposal_merge_requires_and_consumes_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Merge Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    proposal_path = tmp_path / ".p2p" / "proposals" / "PROP-001-mcp-merge-demo" / "proposal.md"
    proposal_path.write_text(proposal_path.read_text(encoding="utf-8") + "\nMCP merge refinement.\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "refine proposal")
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    _git(tmp_path, "checkout", "main")
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_merge",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant proposal merge consent")

    result = call_tool(
        "p2p_proposal_merge",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-001",
        },
    )

    assert result["proposal_merge"]["proposal_id"] == "PROP-001"
    assert result["governance"]["merge_performed"] is True
    assert result["consent"]["status"] == "consumed"
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P consent consume CONSENT-001"
    receipt = yaml.safe_load((tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml").read_text(encoding="utf-8"))
    assert receipt["result"]["merge_commit"] == result["proposal_merge"]["merge_commit"]


def test_mcp_proposal_finalize_requires_and_consumes_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Finalize Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    proposal_path = tmp_path / ".p2p" / "proposals" / "PROP-001-mcp-finalize-demo" / "proposal.md"
    proposal_path.write_text(proposal_path.read_text(encoding="utf-8") + "\nMCP finalize refinement.\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "refine proposal")
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    _git(tmp_path, "checkout", "main")
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_merge",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant proposal merge consent")
    call_tool(
        "p2p_proposal_merge",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-001",
        },
    )
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_finalize",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant proposal finalize consent")

    result = call_tool(
        "p2p_proposal_finalize",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-002",
        },
    )

    assert result["proposal_finalize"]["proposal_id"] == "PROP-001"
    assert result["proposal_finalize"]["base_branch"] == "main"
    assert result["governance"]["finalized"] is True
    assert result["governance"]["cleanup_performed"] is False
    assert result["consent"]["status"] == "consumed"
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P consent consume CONSENT-002"
    assert "refs/heads/main" in _git(tmp_path, "ls-remote", "--heads", "origin", "main").stdout
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-mcp-finalize-demo" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["status"] == "finalized"
    assert data["merge"]["pushed"] is True
    receipt = yaml.safe_load((tmp_path / ".p2p" / "consents" / "CONSENT-002" / "consent.yml").read_text(encoding="utf-8"))
    assert receipt["result"]["finalize_commit"] == result["proposal_finalize"]["finalize_commit"]


def test_mcp_proposal_reject_and_cleanup_require_consent(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "MCP Reject Demo", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))
    runner.invoke(app, ["project", "remote", "configure", "--mode", "remote", "--provider", "generic", "--root", str(tmp_path)])
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["proposal", "branch", "PROP-001", "--actor", "lorenzo", "--root", str(tmp_path)])
    branch_name = _git(tmp_path, "branch", "--show-current").stdout.strip()
    runner.invoke(app, ["proposal", "publish", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_reject_branch",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant proposal reject consent")

    rejected = call_tool(
        "p2p_proposal_reject_branch",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-001",
            "reason": "Not aligned with the current direction.",
        },
    )

    assert rejected["proposal_branch"]["status"] == "rejected"
    assert rejected["governance"]["decision_made"] is True
    assert rejected["governance"]["decision_outcome"] == "rejected"
    assert rejected["consent"]["status"] == "consumed"
    _git(tmp_path, "checkout", "main")
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_cleanup",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "grant proposal cleanup consent")

    cleaned = call_tool(
        "p2p_proposal_cleanup",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-001",
            "delete_remote": True,
        },
    )

    assert cleaned["proposal_cleanup"]["local_deleted"] is True
    assert cleaned["proposal_cleanup"]["remote_deleted"] is True
    assert cleaned["governance"]["cleanup_performed"] is True
    assert cleaned["consent"]["status"] == "consumed"
    assert branch_name not in _git(tmp_path, "branch", "--list", branch_name).stdout
    assert branch_name not in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout
    branch_metadata = tmp_path / ".p2p" / "proposals" / "PROP-001-mcp-reject-demo" / "branch.yml"
    data = yaml.safe_load(branch_metadata.read_text(encoding="utf-8"))
    assert data["status"] == "cleaned"
    assert data["cleanup"]["previous_status"] == "rejected"


def test_mcp_permission_and_consent_read_tools(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "proposal_publish",
            "PROP-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )

    permissions = call_tool("p2p_permissions_show", {"root": str(tmp_path)})
    assert permissions["permissions"]["identities"]["matteo"]["role"] == "owner"
    assert permissions["permissions"]["identities"]["lorenzo"]["role"] == "contributor"

    status = call_tool("p2p_consent_status", {"root": str(tmp_path)})
    assert status["consents"][0]["consent_id"] == "CONSENT-001"
    assert status["consents"][0]["operation"] == "proposal_publish"

    shown = call_tool("p2p_consent_show", {"root": str(tmp_path), "consent_id": "CONSENT-001"})
    assert shown["consent"]["actor_id"] == "lorenzo"


def test_mcp_write_safe_bootstrap_tools(tmp_path: Path) -> None:
    initialized = call_tool(
        "p2p_init_project",
        {
            "root": str(tmp_path),
            "name": "MCP Bootstrap",
            "agent": "codex",
            "repository": "cloud",
            "domain": "software",
        },
    )

    assert initialized["initialized"] is True
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".p2p" / "agent-policy.yml").exists()
    assert (tmp_path / ".p2p" / "project" / "rubrics.yml").exists()
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()

    refreshed = call_tool(
        "p2p_agent_instructions_refresh",
        {"root": str(tmp_path), "profile": "claude"},
    )

    assert refreshed["agent_instructions"]["profile"] == "claude"
    assert (tmp_path / "CLAUDE.md").exists()
    policy_text = (tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8")
    policy = yaml.safe_load(policy_text)
    assert "codex" in policy["agent_profiles"]
    assert "claude" in policy["agent_profiles"]
    assert policy["write_policy"]["analysis_without_write"] == "allowed"
    assert policy["write_policy"]["preview_can_be_skipped_when"] == (
        "owner_requested_exact_operation_and_artifact"
    )
    assert policy["placement_policy"]["mode"] == "strict"
    assert policy["placement_policy"]["unknown_destination"]["behavior"] == "preview_and_ask_or_stop"
    assert policy["artifact_contract_policy"]["agent_must_not_invent_durable_output_paths"] is True
    assert "managed_git_collaboration" in policy
    assert "p2p proposal publish PROP-XXX --auto-renumber" in policy_text
    assert "deferred_permission_gated_mcp_tools" in policy_text
    assert "p2p_proposal_publish" in policy_text
    assert "p2p_work_publish" in policy_text
    assert "p2p_work_accept" in policy_text
    assert "p2p_sync_fetch" in policy_text
    assert "raw_git_managed_branch" in policy_text


def test_mcp_agent_integration_lifecycle_tools(tmp_path: Path) -> None:
    initialized = call_tool(
        "p2p_init_project",
        {
            "root": str(tmp_path),
            "name": "MCP Agents",
            "agent": "cursor",
        },
    )

    assert initialized["initialized"] is True
    listed = call_tool("p2p_agent_list", {"root": str(tmp_path)})
    adapters = {item["adapter"]: item for item in listed["agent_integrations"]["adapters"]}
    assert adapters["generic"]["installed"] is True
    assert adapters["cursor"]["installed"] is True
    assert adapters["codex"]["installed"] is False

    installed = call_tool("p2p_agent_install", {"root": str(tmp_path), "adapter": "gemini"})
    assert installed["agent_integration"]["target"] == "gemini"
    assert (tmp_path / "GEMINI.md").exists()

    shown = call_tool("p2p_agent_show", {"root": str(tmp_path), "adapter": "gemini"})
    assert shown["agent_integration"]["installed"] is True
    assert shown["agent_integration"]["files"][1]["path"] == "GEMINI.md"

    gemini = tmp_path / "GEMINI.md"
    gemini.write_text(gemini.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
    updated = call_tool("p2p_agent_update", {"root": str(tmp_path), "adapter": "gemini"})
    assert updated["agent_integration"]["skipped"][0]["reason"] == "drifted"

    uninstalled = call_tool("p2p_agent_uninstall", {"root": str(tmp_path), "adapter": "gemini"})
    skipped_reasons = {item["reason"] for item in uninstalled["agent_integration"]["skipped"]}
    assert "drifted" in skipped_reasons


def test_mcp_init_default_agent_set_matches_cli_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_CURRENT_AGENT", "codex")
    cli_root = tmp_path / "cli"
    mcp_root = tmp_path / "mcp"
    cli_root.mkdir()
    mcp_root.mkdir()

    cli_result = runner.invoke(app, ["init", "CLI Default", "--root", str(cli_root)])
    mcp_result = call_tool("p2p_init_project", {"root": str(mcp_root), "name": "MCP Default"})

    assert cli_result.exit_code == 0
    assert mcp_result["initialized"] is True
    assert mcp_result["agent_selection"]["selection_source"] == "detected"
    assert mcp_result["agent_selection"]["detected_adapter"] == "codex"
    assert mcp_result["agent_selection"]["effective_adapters"] == ["generic", "codex"]
    cli_registry = yaml.safe_load((cli_root / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    mcp_registry = yaml.safe_load((mcp_root / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert set(mcp_registry["adapters"]) == set(cli_registry["adapters"])


def test_mcp_init_unknown_detection_falls_back_to_all_with_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("P2P_CURRENT_AGENT", raising=False)
    result = call_tool("p2p_init_project", {"root": str(tmp_path), "name": "MCP Default"})

    assert result["initialized"] is True
    assert result["agent_selection"]["selection_source"] == "fallback"
    assert result["agent_selection"]["fallback_used"] is True
    assert "Could not reliably detect the current agent" in result["agent_selection"]["warning"]
    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert set(registry["adapters"]) == {
        "generic",
        "codex",
        "claude",
        "cursor",
        "copilot",
        "gemini",
        "opencode",
    }


def test_mcp_init_returns_additive_mcp_hint_and_hygiene_metadata(tmp_path: Path) -> None:
    result = call_tool("p2p_init_project", {"root": str(tmp_path), "name": "MCP Hint Project", "agent": "generic"})

    assert result["initialized"] is True
    assert result["root"] == str(tmp_path)
    assert "created_or_updated" in result
    assert result["mcp_hint"]["server_name"] == "p2p-mcp-hint-project"
    assert result["mcp_hint"]["server_command"][-2:] == ["--root", str(tmp_path)]
    assert result["mcp_hint"]["fallback_command"] == ["p2p-mcp-server", "--root", str(tmp_path)]
    assert result["gitignore_hygiene"]["status"] == "applied"
    assert result["gitignore_hygiene"]["path"] == ".gitignore"


def test_mcp_agent_uninstall_refuses_generic_baseline(tmp_path: Path) -> None:
    call_tool("p2p_init_project", {"root": str(tmp_path), "name": "MCP Agents", "agent": "cursor"})

    with pytest.raises(ValueError, match="generic cannot be uninstalled"):
        call_tool("p2p_agent_uninstall", {"root": str(tmp_path), "adapter": "generic"})

    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert "generic" in registry["adapters"]


def test_mcp_agent_doctor_returns_structured_findings(tmp_path: Path) -> None:
    call_tool("p2p_init_project", {"root": str(tmp_path), "name": "MCP Doctor", "agent": "generic"})
    clean = call_tool("p2p_agent_doctor", {"root": str(tmp_path), "adapter": "generic"})
    (tmp_path / "AGENTS.md").unlink()

    broken = call_tool("p2p_agent_doctor", {"root": str(tmp_path), "adapter": "generic"})

    assert clean["agent_doctor"]["health"] == "clean"
    assert clean["agent_doctor"]["findings"] == []
    assert broken["agent_doctor"]["health"] == "error"
    assert broken["agent_doctor"]["findings"][0]["code"] == "P2P_AGENT_FILE_MISSING"
    assert broken["agent_doctor"]["findings"][0]["path"] == "AGENTS.md"


def test_mcp_init_project_can_start_with_unresolved_custom_domain(tmp_path: Path) -> None:
    initialized = call_tool(
        "p2p_init_project",
        {
            "root": str(tmp_path),
            "name": "Custom Domain Project",
            "domain": "custom",
        },
    )

    assert initialized["initialized"] is True
    domain = (tmp_path / ".p2p" / "project" / "domain.yml").read_text(encoding="utf-8")
    rubrics = (tmp_path / ".p2p" / "project" / "rubrics.yml").read_text(encoding="utf-8")

    assert "status: unresolved" in domain
    assert "type: custom" in domain
    assert "status: unresolved" in rubrics
    assert "criteria: []" in rubrics

    maturity = call_tool("p2p_maturity_refresh", {"root": str(tmp_path)})

    assert maturity["maturity"]["status"] == "rubric_missing"
    assert maturity["maturity"]["score"] == 0


def test_mcp_registry_refresh_tool(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = call_tool("p2p_registry_refresh", {"root": str(tmp_path)})

    written = result["written"]
    assert ".p2p/registries/proposals.yml" in written
    assert (tmp_path / ".p2p" / "registries" / "proposals.yml").exists()


def test_mcp_validate_returns_structured_findings(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])

    result = call_tool("p2p_validate", {"root": str(tmp_path)})

    validation = result["validation"]
    assert validation["ok"] is True
    assert validation["errors"] == 0
    assert any(finding["code"] == "P2P201_STALE_REGISTRY" for finding in validation["findings"])


def test_mcp_validate_reports_duplicate_proposal_ids(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])
    proposals_dir = tmp_path / ".p2p" / "proposals"
    shutil.copytree(proposals_dir / "PROP-001-draft-work", proposals_dir / "PROP-001-other-draft")

    result = call_tool("p2p_validate", {"root": str(tmp_path)})

    validation = result["validation"]
    assert validation["ok"] is False
    assert validation["errors"] == 1
    duplicate = next(
        finding for finding in validation["findings"] if finding["code"] == "P2P104_DUPLICATE_PROPOSAL_ID"
    )
    assert "Duplicate proposal ID PROP-001" in duplicate["message"]


def test_mcp_assess_refresh_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    call_tool("p2p_proposal_create", {"root": str(tmp_path), "title": "Draft Work"})
    call_tool("p2p_registry_refresh", {"root": str(tmp_path)})

    result = call_tool("p2p_assess_refresh", {"root": str(tmp_path)})

    assessment = result["assessment"]
    assert assessment["completion_score"] < 100
    assert assessment["completion_status"] in {"needs_review", "at_risk"}
    assert assessment["maturity_status"] == "not_assessed"
    assert "Accept at least one proposal when the project direction is clear." in assessment["gaps"]

    shown = call_tool("p2p_assess_show", {"root": str(tmp_path)})

    assert shown["assessment"]["completion_score"] == assessment["completion_score"]
    assert shown["assessment"]["path"] == ".p2p/project/assessment.yml"


def test_mcp_proposal_readiness_tools_are_advisory(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    call_tool("p2p_proposal_create", {"root": str(tmp_path), "title": "Readiness Draft"})

    shown = call_tool("p2p_proposal_readiness_get", {"root": str(tmp_path), "proposal_id": "PROP-001"})

    assert shown["readiness"]["status"] == "not_assessed"
    assert shown["readiness"]["computed_score"] is None

    refreshed = call_tool("p2p_proposal_readiness_refresh", {"root": str(tmp_path), "proposal_id": "PROP-001"})

    assert refreshed["readiness"]["status"] == "not_assessed"
    assert refreshed["governance"]["decision_made"] is False
    assert refreshed["governance"]["override_applied"] is False

    initialized = call_tool("p2p_proposal_readiness_init", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    assessed = call_tool("p2p_proposal_readiness_assess", {"root": str(tmp_path), "proposal_id": "PROP-001"})

    assert initialized["readiness"]["status"] == "assessed"
    assert initialized["readiness"]["computed_score"] is not None
    assert initialized["readiness"]["confidence"] == "low"
    assert initialized["governance"]["decision_made"] is False
    assert assessed["readiness"]["status"] == "assessed"

    explained = call_tool("p2p_proposal_readiness_explain", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    gaps = call_tool("p2p_proposal_readiness_list_gaps", {"root": str(tmp_path), "proposal_id": "PROP-001"})

    assert explained["readiness"]["status"] == "assessed"
    assert gaps["gaps"]["proposal_id"] == "PROP-001"
    assert isinstance(gaps["gaps"]["suggested_next"], list)


def test_mcp_proposal_question_tools_are_write_safe(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    call_tool("p2p_proposal_create", {"root": str(tmp_path), "title": "Question Draft"})
    call_tool("p2p_proposal_readiness_init", {"root": str(tmp_path), "proposal_id": "PROP-001"})

    status = call_tool("p2p_proposal_questions_status", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    initialized = call_tool("p2p_proposal_questions_init", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    added = call_tool(
        "p2p_proposal_questions_add",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "gap": "alternatives_quality",
            "question": "Which alternative should be compared first?",
            "priority": "high",
        },
    )
    answered = call_tool(
        "p2p_proposal_questions_answer",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "question_id": "Q001",
            "answer": "Use a first-class CLI object.",
        },
    )
    applied = call_tool("p2p_proposal_questions_apply", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    review = call_tool("p2p_proposal_readiness_review", {"root": str(tmp_path), "proposal_id": "PROP-001"})

    assert status["questions"]["status"] == "not_initialized"
    assert initialized["questions"]["status"] == "initialized"
    assert added["question"]["question"]["question_id"] == "Q001"
    assert added["governance"]["decision_made"] is False
    assert answered["question"]["question"]["state"] == "answered"
    assert "Q001" in applied["apply"]["summary"]
    assert applied["apply"]["update_plan"]
    assert review["review"]["question_state_status"] == "initialized"
    assert review["review"]["assertiveness_guidance"]


def test_mcp_readiness_tools_include_structured_question_state(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    call_tool("p2p_proposal_create", {"root": str(tmp_path), "title": "Question State"})
    call_tool("p2p_proposal_questions_init", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    call_tool(
        "p2p_proposal_questions_add",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "gap": "owner_questions_resolution",
            "question": "Should structured question state be authoritative?",
            "priority": "high",
        },
    )
    call_tool(
        "p2p_proposal_questions_answer",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "question_id": "Q001",
            "answer": "Yes, structured question state is authoritative.",
        },
    )
    call_tool("p2p_proposal_questions_apply", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-question-state"
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Should stale markdown reopen an applied structured question?\n",
        encoding="utf-8",
    )

    assessed = call_tool("p2p_proposal_readiness_assess", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    explained = call_tool("p2p_proposal_readiness_explain", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    gaps = call_tool("p2p_proposal_readiness_list_gaps", {"root": str(tmp_path), "proposal_id": "PROP-001"})

    owner_state = assessed["readiness"]["owner_question_state"]
    assert owner_state["source"] == "structured"
    assert owner_state["blocking_owner_questions"] == []
    assert [item["id"] for item in owner_state["closed_questions"]] == ["Q001"]
    assert "owner_question_state" in explained["explanation"]
    assert "owner_question_state" in gaps["gaps"]
    assert "owner_questions_resolution:needs_owner_input" not in assessed["readiness"]["failed_gates"]


def test_mcp_context_returns_compact_packet(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    call_tool("p2p_proposal_create", {"root": str(tmp_path), "title": "Draft Work"})
    call_tool("p2p_registry_refresh", {"root": str(tmp_path)})

    result = call_tool("p2p_context", {"root": str(tmp_path), "budget": "small"})

    packet = result["context"]
    assert packet["budget"] == "small"
    assert packet["current_state"]["proposals"] == 1
    assert "Do not scan all .p2p/ directories." in packet["do_not_read"]
    assert any(item["id"] == "PROP-001" for item in packet["relevant_artifacts"])

    targeted = call_tool(
        "p2p_context",
        {"root": str(tmp_path), "budget": "small", "target": "PROP-001"},
    )

    assert targeted["context"]["target"] == "PROP-001"
    assert targeted["context"]["relevant_artifacts"][0]["command"] == "p2p proposal show PROP-001"
    nearby = targeted["context"]["nearby_context"]
    assert nearby["schema_version"] == "decision-context-v1"
    assert nearby["budget"] == "small"
    assert nearby["diagnostics"][0]["code"] == "DC-RETRIEVAL-EMPTY"
    assert nearby == to_jsonable(
        P2PWorkspace(tmp_path).context_packet(
            budget="small",
            target="PROP-001",
        ).nearby_context
    )


def test_mcp_project_definition_maturity(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    rubrics = call_tool(
        "p2p_project_rubrics_init",
        {"root": str(tmp_path), "domain": "software", "force": True},
    )

    assert rubrics["rubrics"]["domain"] == "software"
    assert any(item["id"] == "security_privacy" for item in rubrics["rubrics"]["criteria"])

    call_tool(
        "p2p_proposal_create",
        {
            "root": str(tmp_path),
            "title": "Security Model",
            "problem": "Security and privacy need explicit permission boundaries.",
            "proposal": "Define sandbox permissions.",
        },
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Needed.", "--root", str(tmp_path)])

    maturity = call_tool("p2p_maturity_refresh", {"root": str(tmp_path)})

    assert maturity["maturity"]["domain"] == "software"
    assert maturity["maturity"]["score"] > 0
    security = [
        item for item in maturity["maturity"]["criteria"] if item["id"] == "security_privacy"
    ][0]
    assert security["status"] == "covered"

    shown = call_tool("p2p_maturity_show", {"root": str(tmp_path)})

    assert shown["maturity"]["path"] == ".p2p/project/maturity-assessment.yml"


def test_mcp_proposal_create_creates_draft_only(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = call_tool(
        "p2p_proposal_create",
        {
            "root": str(tmp_path),
            "title": "Perfect Box",
            "problem": "The box is undefined.",
            "goals": ["Define measurable quality criteria."],
            "proposal": "Create a draft specification.",
            "acceptance_criteria": ["Proposal remains draft until owner decision."],
        },
    )

    proposal = result["proposal"]
    assert proposal["proposal_id"] == "PROP-001"
    assert proposal["status"] == "draft"
    assert result["governance"]["owner_decision_required"] is True
    assert result["governance"]["decision_made"] is False

    detail = call_tool("p2p_proposal_show", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    assert detail["proposal"]["status"] == "draft"
    assert detail["proposal"]["decision_status"] == "pending"


def test_mcp_proposal_update_refines_draft_without_deciding(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    created = call_tool(
        "p2p_proposal_create",
        {"root": str(tmp_path), "title": "Refinable Proposal"},
    )

    result = call_tool(
        "p2p_proposal_update",
        {
            "root": str(tmp_path),
            "proposal_id": created["proposal"]["proposal_id"],
            "problem": "The draft needs measurable requirements.",
            "goals": ["Add measurable acceptance criteria."],
            "acceptance_criteria": ["Decision remains pending after refinement."],
        },
    )

    assert result["updated"] == ".p2p/proposals/PROP-001-refinable-proposal/proposal.md"
    assert result["proposal"]["status"] == "draft"
    assert result["proposal"]["decision_status"] == "pending"
    assert result["governance"]["owner_decision_required"] is True

    proposal_text = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-refinable-proposal" / "proposal.md"
    ).read_text(encoding="utf-8")
    assert "The draft needs measurable requirements." in proposal_text
    assert "- Add measurable acceptance criteria." in proposal_text
    assert "- Decision remains pending after refinement." in proposal_text


def test_mcp_proposal_contribution_add_does_not_decide(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    created = call_tool(
        "p2p_proposal_create",
        {"root": str(tmp_path), "title": "Criteria Proposal"},
    )

    result = call_tool(
        "p2p_proposal_contribution_add",
        {
            "root": str(tmp_path),
            "proposal_id": created["proposal"]["proposal_id"],
            "text": "The box should be easy to position and transport.",
            "type": "objective",
            "relevance": "high",
            "author": "mcp-test",
        },
    )

    assert result["contribution"]["contribution_id"] == "C001"
    assert result["contribution"]["contribution_type"] == "objective"
    assert result["contribution"]["author"] == "mcp-test"
    assert result["proposal"]["decision_status"] == "pending"
    assert result["governance"]["decision_made"] is False

    listed = call_tool(
        "p2p_proposal_contribution_list",
        {"root": str(tmp_path), "proposal_id": created["proposal"]["proposal_id"]},
    )

    assert listed["contributions"]["proposal_id"] == "PROP-001"
    assert listed["contributions"]["contributions"][0]["contribution_id"] == "C001"
    assert listed["contributions"]["contributions"][0]["text"] == "The box should be easy to position and transport."

    contributions = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-criteria-proposal" / "contributions.yml"
    ).read_text(encoding="utf-8")
    assert "The box should be easy to position and transport." in contributions
    assert "relevance_hint: high" in contributions


def test_mcp_intake_prompt_and_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    prompt = call_tool(
        "p2p_intake_prompt",
        {"root": str(tmp_path), "idea": "A new idea that may overlap existing work."},
    )

    assert prompt["intake"]["intake_id"] == "INTAKE-001"
    assert set(prompt["intake"]) == {"intake_id", "path", "prompt_path"}
    assert (tmp_path / ".p2p" / "intake" / "INTAKE-001" / "intake.prompt.md").exists()

    status = call_tool("p2p_intake_status", {"root": str(tmp_path)})
    assert status["intake_status"][0]["intake_id"] == "INTAKE-001"


def test_mcp_project_brief_prompt_and_show(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    prompt = call_tool("p2p_project_brief_prompt", {"root": str(tmp_path)})

    assert prompt["project_brief_prompt"]["context_path"] == ".p2p/project/brief-context.md"
    assert prompt["project_brief_prompt"]["prompt_path"] == ".p2p/project/brief.prompt.md"
    assert (tmp_path / ".p2p" / "project" / "brief.prompt.md").exists()

    brief_path = tmp_path / ".p2p" / "project" / "operational-brief.md"
    brief_path.write_text("# Operational Brief\n\nDraft summary.\n", encoding="utf-8")

    shown = call_tool("p2p_project_brief_show", {"root": str(tmp_path)})

    assert "Draft summary." in shown["operational_brief"]


def test_mcp_choice_discover_is_advisory(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Open direction",
            "--option",
            "A",
            "--option",
            "B",
            "--root",
            str(tmp_path),
        ],
    )

    result = call_tool("p2p_choice_discover", {"root": str(tmp_path)})

    assert result["choice_discovery"][0]["kind"] == "open_project_choice"
    assert result["choice_discovery"][0]["target"] == "CHOICE-001"
    detail = call_tool("p2p_choice_show", {"root": str(tmp_path), "choice_id": "CHOICE-001"})
    assert detail["choice"]["status"] == "open"


def test_mcp_conflict_status_reads_without_recording(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = call_tool("p2p_conflict_status", {"root": str(tmp_path)})

    assert result["conflicts"]["conflicts_count"] == 0
    assert result["conflicts"]["conflicts"] == []


def test_mcp_impact_prompt_generates_prompt_only(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    created = call_tool(
        "p2p_proposal_create",
        {"root": str(tmp_path), "title": "Impact Candidate"},
    )

    result = call_tool(
        "p2p_impact_prompt",
        {"root": str(tmp_path), "proposal_id": created["proposal"]["proposal_id"]},
    )

    assert result["impact_prompt"]["path"] == ".p2p/prompts/PROP-001/impact.prompt.md"
    assert (tmp_path / ".p2p" / "prompts" / "PROP-001" / "impact.prompt.md").exists()
    assert not (
        tmp_path / ".p2p" / "proposals" / "PROP-001-impact-candidate" / "impact-map.yml"
    ).exists()
    detail = call_tool("p2p_proposal_show", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    assert detail["proposal"]["decision_status"] == "pending"


def test_mcp_call_tool_reads_project_state(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    result = call_tool("p2p_project_status", {"root": str(tmp_path)})

    assert result["project_status"]["accepted_proposals"] == 1
    assert result["project_status"]["operational_brief_available"] is False


def test_mcp_change_project_registry_and_remote_read_tools(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    change = call_tool("p2p_change_show", {"root": str(tmp_path), "change_id": "CHANGE-001"})
    tasks = call_tool("p2p_change_tasks", {"root": str(tmp_path), "change_id": "CHANGE-001"})
    registry = call_tool("p2p_registry_status", {"root": str(tmp_path)})
    project = call_tool("p2p_project_show", {"root": str(tmp_path), "section": "overview"})
    remote = call_tool("p2p_project_remote_show", {"root": str(tmp_path)})

    assert change["change"]["change_id"] == "CHANGE-001"
    assert tasks["tasks"]["change_id"] == "CHANGE-001"
    assert registry["registry_status"]["proposals_count"] == 1
    assert "# Project State - Demo Project" in project["content"]
    assert remote["remote"]["mode"] == "local"


def test_mcp_write_safe_spec_export_and_work_flow(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    lifecycle = call_tool(
        "p2p_spec_lifecycle",
        {"root": str(tmp_path), "intent": "implementation_spec", "change_id": "CHANGE-001"},
    )
    spec = call_tool("p2p_spec_refresh", {"root": str(tmp_path), "change_id": "CHANGE-001"})
    export = call_tool(
        "p2p_spec_export",
        {"root": str(tmp_path), "change_id": "CHANGE-001", "target": "generic"},
    )
    validation = call_tool(
        "p2p_spec_export_validate",
        {"root": str(tmp_path), "change_id": "CHANGE-001", "target": "generic"},
    )
    work = call_tool(
        "p2p_work_plan",
        {"root": str(tmp_path), "change_id": "CHANGE-001", "target": "generic"},
    )

    assert lifecycle["lifecycle"]["route"] == "preflight_change_set_then_refresh_software_spec"
    assert lifecycle["lifecycle"]["blockers"] == []
    assert spec["spec"]["status"] == "generated"
    assert spec["spec"]["lifecycle"]["route"] == "preflight_change_set_then_refresh_software_spec"
    assert export["export"]["status"] == "exported"
    assert export["export"]["lifecycle"]["route"] == "preflight_spec_then_export_target"
    assert validation["validation"]["target"] == "generic"
    assert work["work"]["work_id"] == "WORK-001"
    assert work["work"]["status"] == "planned"

    spec_status = call_tool("p2p_spec_status", {"root": str(tmp_path)})
    spec_show = call_tool("p2p_spec_show", {"root": str(tmp_path), "change_id": "CHANGE-001"})
    export_status = call_tool("p2p_spec_export_status", {"root": str(tmp_path)})
    export_show = call_tool(
        "p2p_spec_export_show",
        {"root": str(tmp_path), "change_id": "CHANGE-001", "target": "generic"},
    )
    work_list = call_tool("p2p_work_list", {"root": str(tmp_path)})
    work_show = call_tool("p2p_work_show", {"root": str(tmp_path), "work_id": "WORK-001"})

    assert spec_status["specs"][0]["change_id"] == "CHANGE-001"
    assert "CHANGE-001" in spec_show["content"]
    assert export_status["exports"][0]["target"] == "generic"
    assert "# Demo Project Project Definition" in export_show["content"]
    assert work_list["work"][0]["work_id"] == "WORK-001"
    assert work_show["work"]["change_id"] == "CHANGE-001"


def test_mcp_work_lifecycle_tools_are_callable_through_public_dispatch(tmp_path: Path) -> None:
    _setup_work_lifecycle_project(tmp_path)

    branched = call_tool("p2p_work_branch", {"root": str(tmp_path), "work_id": "WORK-001"})
    branch_name = branched["work_branch"]["branch_name"]
    assert branched["work_branch"]["work_id"] == "WORK-001"
    assert branched["governance"]["owner_decision_required"] is False

    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "work_demo.py").write_text("VALUE = 1\n", encoding="utf-8")
    submitted = call_tool("p2p_work_submit", {"root": str(tmp_path), "work_id": "WORK-001"})
    reviewed = call_tool("p2p_work_review", {"root": str(tmp_path), "work_id": "WORK-001"})

    assert any(path.startswith("src/") for path in submitted["work_submit"]["changed_files"])
    assert submitted["governance"]["merge_performed"] is False
    assert reviewed["work_review"]["metadata_commit"]

    published = call_tool(
        "p2p_work_publish",
        {
            "root": str(tmp_path),
            "work_id": "WORK-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-001",
        },
    )
    review_requested = call_tool(
        "p2p_work_request_review",
        {
            "root": str(tmp_path),
            "work_id": "WORK-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-002",
            "provider": "github",
        },
    )

    assert published["work_publish"]["remote"] == "origin"
    assert published["governance"]["published"] is True
    assert published["consent"]["status"] == "consumed"
    assert branch_name in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout
    assert review_requested["work_review_request"]["provider"] == "github"
    assert review_requested["governance"]["external_review_requested"] is True
    assert review_requested["work_review_request"]["suggested_next"]

    _git(tmp_path, "checkout", "main")
    accepted = call_tool(
        "p2p_work_accept",
        {
            "root": str(tmp_path),
            "work_id": "WORK-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-003",
        },
    )
    finalized = call_tool(
        "p2p_work_finalize",
        {
            "root": str(tmp_path),
            "work_id": "WORK-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-004",
        },
    )
    cleaned = call_tool(
        "p2p_work_cleanup",
        {
            "root": str(tmp_path),
            "work_id": "WORK-001",
            "actor_id": "lorenzo",
            "consent_id": "CONSENT-005",
            "delete_remote": True,
        },
    )

    assert accepted["governance"]["merge_performed"] is True
    assert accepted["governance"]["finalized"] is False
    assert accepted["consent"]["status"] == "consumed"
    assert finalized["work_finalize"]["base_branch"] == "main"
    assert finalized["governance"]["finalized"] is True
    assert finalized["governance"]["cleanup_performed"] is False
    assert cleaned["work_cleanup"]["local_deleted"] is True
    assert cleaned["work_cleanup"]["remote_deleted"] is True
    assert cleaned["governance"]["cleanup_performed"] is True
    assert branch_name not in _git(tmp_path, "branch", "--list", branch_name).stdout
    assert branch_name not in _git(tmp_path, "ls-remote", "--heads", "origin", branch_name).stdout


def test_mcp_work_publish_rejects_consent_actor_mismatch_before_lifecycle(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["init", "Demo Project", "--owner", "matteo", "--root", str(tmp_path)])
    runner.invoke(app, ["permissions", "actor", "add", "lorenzo", "--role", "contributor", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "consent",
            "grant",
            "work_publish",
            "WORK-001",
            "--actor",
            "lorenzo",
            "--approved-by",
            "matteo",
            "--root",
            str(tmp_path),
        ],
    )

    with pytest.raises(ValueError, match="Consent receipt actor mismatch"):
        call_tool(
            "p2p_work_publish",
            {
                "root": str(tmp_path),
                "work_id": "WORK-001",
                "actor_id": "matteo",
                "consent_id": "CONSENT-001",
            },
        )

    receipt = yaml.safe_load((tmp_path / ".p2p" / "consents" / "CONSENT-001" / "consent.yml").read_text(encoding="utf-8"))
    assert receipt["status"] == "granted"


def test_mcp_work_lifecycle_tools_validate_required_arguments(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    with pytest.raises(ValueError, match="Missing required argument: work_id"):
        call_tool("p2p_work_branch", {"root": str(tmp_path)})
    with pytest.raises(ValueError, match="Missing required argument: actor_id"):
        call_tool("p2p_work_publish", {"root": str(tmp_path), "work_id": "WORK-001", "consent_id": "CONSENT-001"})


def test_mcp_change_create_is_metadata_only_for_accepted_proposal(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    call_tool("p2p_proposal_create", {"root": str(tmp_path), "title": "Accepted Candidate"})
    runner.invoke(
        app,
        ["proposal", "accept", "PROP-001", "--reason", "Ready for metadata-only change.", "--root", str(tmp_path)],
    )

    result = call_tool("p2p_change_create", {"root": str(tmp_path), "source": "PROP-001"})

    assert result["change"]["change_id"] == "CHANGE-001"
    assert result["change"]["status"] == "proposed"
    assert not (tmp_path / ".git").exists()


def test_mcp_project_refresh_writes_generated_project_files(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    result = call_tool("p2p_project_refresh", {"root": str(tmp_path)})

    assert ".p2p/project/overview.md" in result["written"]
    assert (tmp_path / ".p2p" / "project" / "overview.md").exists()


def test_mcp_prompt_tools_generate_prompts_without_importing_outputs(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    prompt_tools = {
        "p2p_explore_prompt": "explore",
        "p2p_digest_prompt": "digest",
        "p2p_clarify_prompt": "clarify",
        "p2p_synthesize_prompt": "synthesize",
        "p2p_plan_prompt": "plan",
        "p2p_tasks_prompt": "tasks",
        "p2p_swot_prompt": "swot",
    }
    for tool, kind in prompt_tools.items():
        result = call_tool(tool, {"root": str(tmp_path), "proposal_id": "PROP-001"})
        assert set(result[f"{kind}_prompt"]) == {"path"}
        assert result[f"{kind}_prompt"]["path"] == f".p2p/prompts/PROP-001/{kind}.prompt.md"
        assert (tmp_path / ".p2p" / "prompts" / "PROP-001" / f"{kind}.prompt.md").exists()

    spec_prompt = call_tool("p2p_spec_prompt", {"root": str(tmp_path), "change_id": "CHANGE-001"})

    assert spec_prompt["spec_prompt"]["prompt_path"] == (
        ".p2p/outputs/software-spec/CHANGE-001/spec-refine.prompt.md"
    )
    detail = call_tool("p2p_proposal_show", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    assert detail["proposal"]["decision_status"] == "accepted"


def test_mcp_artifact_import_tools_import_content_without_deciding(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    result = call_tool(
        "p2p_clarify_import",
        {
            "root": str(tmp_path),
            "proposal_id": "PROP-001",
            "content": "# Clarifications\n\nImported through MCP.\n",
        },
    )

    assert result["artifact_import"]["proposal_id"] == "PROP-001"
    assert result["artifact_import"]["kind"] == "clarify"
    assert result["artifact_import"]["input_mode"] == "content"
    assert result["artifact_import"]["imported"][0]["filename"] == "clarifications.md"
    assert result["artifact_import"]["artifact_state_updated"] is False
    assert result["governance"]["decision_made"] is False
    assert (tmp_path / ".p2p" / "proposals" / "PROP-001-mcp-demo" / "clarifications.md").read_text(
        encoding="utf-8"
    ) == "# Clarifications\n\nImported through MCP.\n"


def test_mcp_jsonrpc_lists_and_calls_tools(tmp_path: Path) -> None:
    _setup_project(tmp_path)

    initialize = handle_message(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        default_root=tmp_path,
    )
    assert initialize is not None
    assert initialize["result"]["serverInfo"]["name"] == "p2p-engine"
    assert initialize["result"]["serverInfo"]["version"] == __version__

    listed = handle_message(
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
        default_root=tmp_path,
    )
    assert listed is not None
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert "p2p_proposal_list" in names
    assert "p2p_tasks_import" in names

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

    imported = handle_message(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "p2p_tasks_import",
                    "arguments": {"proposal_id": "PROP-001", "content": "tasks: []\n"},
                },
            }
        ),
        default_root=tmp_path,
    )
    assert imported is not None
    import_payload = json.loads(imported["result"]["content"][0]["text"])
    assert import_payload["artifact_import"]["imported"][0]["filename"] == "tasks.yml"
    assert payload["proposal"]["title"] == "MCP Demo"
