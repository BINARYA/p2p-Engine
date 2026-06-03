from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.mcp.server import handle_message
from p2p_engine.mcp.tools import TOOL_NAMES, call_tool, tool_definitions

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


def test_mcp_tool_definitions_expose_agent_safe_surface() -> None:
    names = {tool["name"] for tool in tool_definitions()}

    assert set(TOOL_NAMES) == names

    expected = {
        "p2p_init_project",
        "p2p_agent_instructions_refresh",
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
        "p2p_intake_prompt",
        "p2p_intake_status",
        "p2p_project_brief_prompt",
        "p2p_project_brief_show",
        "p2p_choice_discover",
        "p2p_conflict_status",
        "p2p_impact_prompt",
        "p2p_project_status",
        "p2p_next",
        "p2p_proposal_list",
        "p2p_proposal_show",
        "p2p_choice_list",
        "p2p_choice_show",
        "p2p_change_status",
        "p2p_change_show",
        "p2p_change_tasks",
        "p2p_work_list",
        "p2p_work_status",
        "p2p_work_show",
        "p2p_registry_status",
        "p2p_registry_show",
        "p2p_project_show",
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
        "p2p_proposal_accept_branch",
        "p2p_proposal_reject_branch",
        "p2p_proposal_merge",
        "p2p_proposal_finalize",
        "p2p_proposal_cleanup",
        "p2p_proposal_branch_scan",
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
    allowed_decision_tools = {"p2p_proposal_accept_branch", "p2p_proposal_reject_branch"}
    allowed_cleanup_tools = {"p2p_proposal_cleanup"}
    assert not any(
        ("accept" in name and name not in allowed_decision_tools)
        or ("reject" in name and name not in allowed_decision_tools)
        or "defer" in name
        or "decide" in name
        or ("cleanup" in name and name not in allowed_cleanup_tools)
        or (("merge" in name) and name != "p2p_proposal_merge")
        or "contribution_accept" in name
        or "record_conflict" in name
        or "block" in name
        or "retire_branch" in name
        or "consent_grant" in name
        or "consent_revoke" in name
        for name in names
    )


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
    policy = (tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8")
    assert "- codex" in policy
    assert "- claude" in policy
    assert "managed_git_collaboration" in policy
    assert "p2p proposal publish PROP-XXX --auto-renumber" in policy
    assert "deferred_permission_gated_mcp_tools" in policy
    assert "p2p_proposal_publish" in policy
    assert "p2p_sync_fetch" in policy
    assert "raw_git_managed_branch" in policy


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

    assert spec["spec"]["status"] == "generated"
    assert export["export"]["status"] == "exported"
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
        assert result[f"{kind}_prompt"]["path"] == f".p2p/prompts/PROP-001/{kind}.prompt.md"
        assert (tmp_path / ".p2p" / "prompts" / "PROP-001" / f"{kind}.prompt.md").exists()

    spec_prompt = call_tool("p2p_spec_prompt", {"root": str(tmp_path), "change_id": "CHANGE-001"})

    assert spec_prompt["spec_prompt"]["prompt_path"] == (
        ".p2p/outputs/software-spec/CHANGE-001/spec-refine.prompt.md"
    )
    detail = call_tool("p2p_proposal_show", {"root": str(tmp_path), "proposal_id": "PROP-001"})
    assert detail["proposal"]["decision_status"] == "accepted"


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
