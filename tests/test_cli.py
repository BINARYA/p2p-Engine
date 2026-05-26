from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app

runner = CliRunner()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_cli_init_status_create_and_prompt_flow(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "P2P workspace initialized" in result.output

    result = runner.invoke(app, ["status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project: Demo Project" in result.output
    assert "Proposals: none" in result.output

    result = runner.invoke(app, ["check", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Workspace OK" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Exploration Phase",
            "--problem",
            "Ideas need structured exploration.",
            "--goal",
            "Generate exploration prompts.",
            "--acceptance",
            "explore prompt creates a file.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "id: PROP-001" in result.output

    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-exploration-phase"
    proposal = (proposal_dir / "proposal.md").read_text(encoding="utf-8")
    assert "Ideas need structured exploration." in proposal
    assert "- Generate exploration prompts." in proposal
    assert (proposal_dir / "findings.md").exists()

    result = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "add",
            "PROP-001",
            "Explore rough ideas before synthesis.",
            "--type",
            "objective",
            "--relevance",
            "high",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Contribution added" in result.output

    result = runner.invoke(app, ["explore", "prompt", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert ".p2p/prompts/PROP-001/explore.prompt.md" in result.output

    prompt = (tmp_path / ".p2p" / "prompts" / "PROP-001" / "explore.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "P2P Exploration Prompt" in prompt
    assert "findings.md" in prompt

    result = runner.invoke(app, ["explore", "status", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Exploration status for PROP-001" in result.output
    assert "open-questions.md" in result.output


def test_cli_import_exploration_file_and_record_decision(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Decision Flow", "--root", str(tmp_path)])

    source = tmp_path / "exploration-output.md"
    source.write_text("# Exploration\n\nConcrete exploration output.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["explore", "import", "PROP-001", str(source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Exploration imported" in result.output

    result = runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Scope is clear enough.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Decision recorded" in result.output

    decision = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-decision-flow" / "decision.md"
    ).read_text(encoding="utf-8")
    assert "Scope is clear enough." in decision


def test_cli_proposal_decision_shortcuts(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Acceptable Work", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Rejected Work", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Deferred Work", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Ready for implementation.",
            "--approver",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Proposal decision recorded" in result.output
    assert "outcome: accepted" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "reject",
            "PROP-002",
            "--reason",
            "Out of scope.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "outcome: rejected" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "defer",
            "PROP-003",
            "--reason",
            "Needs more context.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "outcome: deferred" in result.output

    result = runner.invoke(app, ["status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001  PROP-001-acceptable-work  accepted" in result.output
    assert "PROP-002  PROP-002-rejected-work  rejected" in result.output
    assert "PROP-003  PROP-003-deferred-work  deferred" in result.output

    decision = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-acceptable-work" / "decision.md"
    ).read_text(encoding="utf-8")
    assert "Ready for implementation." in decision
    assert "owner" in decision


def test_cli_proposal_list_show_and_choice_registry_output(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "CLI Inspection",
            "--problem",
            "Agents need stable proposal inspection.",
            "--proposal",
            "Add proposal list and show commands.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Useful for agent skills.",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["proposal", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001  accepted  CLI Inspection" in result.output

    result = runner.invoke(app, ["proposal", "list", "--status", "draft", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001" not in result.output

    result = runner.invoke(app, ["proposal", "show", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PROP-001 - CLI Inspection" in result.output
    assert "Agents need stable proposal inspection." in result.output
    assert "Add proposal list and show commands." in result.output
    assert "Useful for agent skills." in result.output

    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Inspection Strategy",
            "--option",
            "A",
            "--option",
            "B",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "choice",
            "decide",
            "CHOICE-001",
            "--option",
            "A",
            "--reason",
            "Pick A.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["registry", "show", "choices", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001: decided  Inspection Strategy -> A - A" in result.output
    assert "{" not in result.output


def test_cli_missing_proposal_returns_clean_error(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])

    result = runner.invoke(app, ["digest", "prompt", "PROP-999", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error: Proposal not found: PROP-999" in result.output
    assert "Traceback" not in result.output


def test_cli_prompt_only_import_workflow_to_tasks(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Import Workflow", "--root", str(tmp_path)])

    clarify_source = tmp_path / "clarification-output.md"
    clarify_source.write_text("# Clarifications\n\nQ1 answered.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["clarify", "import", "PROP-001", str(clarify_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "clarifications.md" in result.output

    result = runner.invoke(app, ["synthesize", "prompt", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "synthesize.prompt.md" in result.output

    proposal_source = tmp_path / "proposal-output.md"
    proposal_source.write_text("# PROP-001 - Import Workflow\n\n## Status\n\n`ready_for_review`\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["synthesize", "import", "PROP-001", str(proposal_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "proposal.md" in result.output

    plan_source = tmp_path / "plan-output.md"
    plan_source.write_text("# Execution Plan\n\nImplement imports.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["plan", "import", "PROP-001", str(plan_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "execution-plan.md" in result.output

    tasks_source = tmp_path / "tasks-output.yml"
    tasks_source.write_text(
        "tasks:\n"
        "  - id: T001\n"
        "    title: Implement imports\n"
        "    workstream: WS1\n"
        "    type: software\n"
        "    status: todo\n"
        "    priority: high\n"
        "    dependencies: []\n"
        "    deliverable: CLI commands\n"
        "    evidence_required: Tests pass\n"
        "    actions: []\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["tasks", "import", "PROP-001", str(tasks_source), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "tasks.yml" in result.output

    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-import-workflow"
    assert "Q1 answered." in (proposal_dir / "clarifications.md").read_text(encoding="utf-8")
    assert "ready_for_review" in (proposal_dir / "proposal.md").read_text(encoding="utf-8")
    assert "Implement imports." in (proposal_dir / "execution-plan.md").read_text(encoding="utf-8")
    assert "Implement imports" in (proposal_dir / "tasks.yml").read_text(encoding="utf-8")


def test_cli_tasks_import_rejects_invalid_yaml_shape(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Import Workflow", "--root", str(tmp_path)])
    source = tmp_path / "bad-tasks.yml"
    source.write_text("not_tasks: []\n", encoding="utf-8")

    result = runner.invoke(app, ["tasks", "import", "PROP-001", str(source), "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "expected top-level `tasks` list" in result.output


def test_cli_governance_swot_vote_and_precedent_flow(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Governance Model", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["governance", "init", "--mode", "exclusive_vote", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Governance initialized" in result.output

    result = runner.invoke(app, ["governance", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "mode: exclusive_vote" in result.output

    result = runner.invoke(app, ["swot", "prompt", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "swot.prompt.md" in result.output
    swot_prompt = (tmp_path / ".p2p" / "prompts" / "PROP-001" / "swot.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "P2P SWOT Prompt" in swot_prompt
    assert "exclusive_vote" in swot_prompt

    result = runner.invoke(
        app,
        [
            "vote",
            "record",
            "PROP-001",
            "--choice",
            "ALT-A",
            "--reason",
            "Keeps governance simple.",
            "--voter",
            "davide",
            "--role",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Vote recorded" in result.output
    assert "current winner: ALT-A" in result.output

    result = runner.invoke(app, ["vote", "status", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "ALT-A: 1" in result.output

    result = runner.invoke(
        app,
        [
            "precedent",
            "record",
            "PROP-001",
            "--title",
            "Governance is audit-only in MVP",
            "--reason",
            "Privileges are delegated to Git hosting for now.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Precedent recorded" in result.output

    precedents = (
        tmp_path / ".p2p" / "governance" / "decision-precedents.yml"
    ).read_text(encoding="utf-8")
    assert "Governance is audit-only in MVP" in precedents


def test_cli_project_refresh_status_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "CLI Foundation",
            "--problem",
            "The project needs a first CLI.",
            "--goal",
            "Create p2p init.",
            "--proposal",
            "Build a Git-native CLI foundation.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Required for bootstrap.",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project state refreshed" in result.output
    assert ".p2p/project/overview.md" in result.output
    assert ".p2p/project/features/cli-foundation/feature.md" in result.output

    result = runner.invoke(app, ["project", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "accepted proposals: 1" in result.output
    assert "cli-foundation" in result.output

    result = runner.invoke(app, ["project", "show", "cli-foundation", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CLI Foundation" in result.output
    assert "PROP-001" in result.output
    assert "Required for bootstrap." in result.output

    decisions_map = (tmp_path / ".p2p" / "project" / "decisions-map.yml").read_text(
        encoding="utf-8"
    )
    assert "proposal: PROP-001" in decisions_map


def test_cli_impact_import_and_conflict_memory(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Project State", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Alternative State", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Chosen baseline.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["impact", "prompt", "PROP-002", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "impact.prompt.md" in result.output
    prompt = (tmp_path / ".p2p" / "prompts" / "PROP-002" / "impact.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "P2P Impact Prompt" in prompt
    assert "Existing Project Decisions" in prompt

    source_dir = tmp_path / "impact-output"
    source_dir.mkdir()
    (source_dir / "impact-map.yml").write_text(
        "impact:\n"
        "  proposal: PROP-002\n"
        "  features:\n"
        "    - project-state\n",
        encoding="utf-8",
    )
    (source_dir / "related-proposals.yml").write_text(
        "related_proposals:\n"
        "  - proposal: PROP-001\n"
        "    relationship: mutually_exclusive\n",
        encoding="utf-8",
    )
    (source_dir / "conflict-analysis.yml").write_text(
        "conflicts:\n"
        "  - type: mutually_exclusive\n"
        "    proposals:\n"
        "      - PROP-001\n"
        "      - PROP-002\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["impact", "import", "PROP-002", str(source_dir), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "impact-map.yml" in result.output
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-002-alternative-state"
    assert (proposal_dir / "impact-map.yml").exists()

    result = runner.invoke(
        app,
        [
            "conflict",
            "record",
            "PROP-001",
            "PROP-002",
            "--type",
            "mutually_exclusive",
            "--reason",
            "Two alternative project-state models.",
            "--winner",
            "PROP-001",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Conflict recorded" in result.output

    result = runner.invoke(app, ["conflict", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CONFLICT-001" in result.output
    assert "PROP-001, PROP-002" in result.output

    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    conflicts = (tmp_path / ".p2p" / "project" / "conflicts.yml").read_text(encoding="utf-8")
    assert "CONFLICT-001" in conflicts


def test_cli_change_create_status_and_policy(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Draft Work", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "PROP-001 is not accepted yet" in result.output

    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Ready for operational work.",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Change Set created" in result.output
    assert "id: CHANGE-001" in result.output

    change_dir = tmp_path / ".p2p" / "changes" / "CHANGE-001-draft-work"
    assert (change_dir / "change.md").exists()
    assert (change_dir / "git-policy.yml").exists()
    change_text = (change_dir / "change.md").read_text(encoding="utf-8")
    assert "implementation_targets:" in change_text
    assert "- local_cli" in change_text
    assert "spec_targets:" in change_text
    assert "- p2p_spec" in change_text
    assert "export_targets:" in change_text
    assert "- openspec" in change_text
    assert "- speckit" in change_text
    assert "operation_level: metadata_only" in (change_dir / "git-policy.yml").read_text(
        encoding="utf-8"
    )

    result = runner.invoke(app, ["change", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001" in result.output
    assert "proposed" in result.output

    result = runner.invoke(app, ["change", "policy", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "operation_level: metadata_only" in result.output
    assert "auto_branch: False" in result.output


def test_cli_change_lifecycle_show_and_tasks(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Lifecycle Work", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Ready for lifecycle tracking.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["change", "set-status", "CHANGE-001", "completed", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "Invalid Change Set transition" in result.output

    for status in ("planned", "implementation_ready", "in_progress", "in_review", "completed"):
        result = runner.invoke(
            app,
            ["change", "set-status", "CHANGE-001", status, "--root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert f"status: {status}" in result.output

    result = runner.invoke(app, ["change", "show", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001" in result.output
    assert "completed" in result.output
    assert "execution_domains: software" in result.output
    assert "implementation_targets: local_cli" in result.output
    assert "spec_targets: p2p_spec" in result.output
    assert "export_targets: openspec, speckit" in result.output

    change_dir = tmp_path / ".p2p" / "changes" / "CHANGE-001-lifecycle-work"
    (change_dir / "actions.yml").write_text(
        "actions:\n"
        "  - id: A001\n"
        "    title: Verify lifecycle output\n"
        "    checked: true\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["change", "tasks", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Tasks for CHANGE-001" in result.output
    assert "[x] A001: Verify lifecycle output" in result.output


def test_cli_registry_refresh_status_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Project Registries", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Needed for project navigation.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["registry", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "stale: True" in result.output

    result = runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Registries refreshed" in result.output
    assert ".p2p/registries/proposals.yml" in result.output
    assert ".p2p/registries/changes.yml" in result.output

    registries_dir = tmp_path / ".p2p" / "registries"
    assert (registries_dir / "proposals.yml").exists()
    assert (registries_dir / "changes.yml").exists()
    assert "generated: true" in (registries_dir / "proposals.yml").read_text(encoding="utf-8")
    assert "id: PROP-001" in (registries_dir / "proposals.yml").read_text(encoding="utf-8")
    changes_registry = (registries_dir / "changes.yml").read_text(encoding="utf-8")
    assert "id: CHANGE-001" in changes_registry
    assert "spec_targets:" in changes_registry
    assert "- p2p_spec" in changes_registry
    assert "export_targets:" in changes_registry
    assert "- openspec" in changes_registry
    assert "- speckit" in changes_registry

    result = runner.invoke(app, ["registry", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "stale: False" in result.output
    assert "proposals.yml (1 records)" in result.output
    assert "changes.yml (1 records)" in result.output

    result = runner.invoke(app, ["registry", "show", "proposals", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Registry: proposals" in result.output
    assert "PROP-001: accepted  Project Registries" in result.output

    result = runner.invoke(app, ["registry", "show", "changes", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Registry: changes" in result.output
    assert "CHANGE-001: proposed  Project Registries" in result.output


def test_cli_software_spec_refresh_prompt_import_status_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Spec Work",
            "--problem",
            "Need implementation-facing specs.",
            "--proposal",
            "Generate a deterministic software spec.",
            "--acceptance",
            "Spec artifacts exist.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Needed before export.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software spec refreshed" in result.output
    assert ".p2p/outputs/software-spec/CHANGE-001" in result.output

    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    for filename in (
        "index.md",
        "requirements.md",
        "design.md",
        "commands.yml",
        "data-model.yml",
        "acceptance.md",
        "provenance.yml",
    ):
        assert (spec_dir / filename).exists()
    assert "Spec Work" in (spec_dir / "index.md").read_text(encoding="utf-8")
    assert "Generate a deterministic software spec." in (spec_dir / "requirements.md").read_text(
        encoding="utf-8"
    )
    assert "source:" in (spec_dir / "provenance.yml").read_text(encoding="utf-8")

    result = runner.invoke(app, ["spec", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001  generated  Spec Work" in result.output

    result = runner.invoke(app, ["spec", "show", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software Spec - CHANGE-001 - Spec Work" in result.output

    result = runner.invoke(app, ["spec", "prompt", "--change", "CHANGE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software spec prompt created" in result.output
    prompt = (spec_dir / "spec-refine.prompt.md").read_text(encoding="utf-8")
    assert "P2P Software Spec Refinement Prompt" in prompt
    assert "Do not add requirements" in prompt

    refined_dir = tmp_path / "refined-spec"
    refined_dir.mkdir()
    for filename in ("index.md", "requirements.md", "design.md", "acceptance.md"):
        (refined_dir / filename).write_text(f"# {filename}\n\nRefined.\n", encoding="utf-8")
    (refined_dir / "commands.yml").write_text("commands: []\n", encoding="utf-8")
    (refined_dir / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (refined_dir / "provenance.yml").write_text(
        "source:\n  change: CHANGE-001\n  included_proposals:\n    - PROP-001\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["spec", "import", "CHANGE-001", str(refined_dir), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Software spec imported" in result.output
    assert "Refined." in (spec_dir / "index.md").read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "generic", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Software spec exported" in result.output
    assert ".p2p/outputs/spec-export/CHANGE-001/generic" in result.output

    generic_dir = tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "generic"
    assert (generic_dir / "index.md").exists()
    assert (generic_dir / "requirements.md").exists()
    assert (generic_dir / "manifest.yml").exists()
    assert "Generic Software Spec Export" in (generic_dir / "index.md").read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0

    openspec_dir = tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "openspec"
    assert (openspec_dir / "index.md").exists()
    assert (openspec_dir / "spec.md").exists()
    assert "OpenSpec-Oriented Specification" in (openspec_dir / "spec.md").read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0

    speckit_dir = tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "speckit"
    speckit_feature_dir = speckit_dir / "specs" / "change-001-spec-work"
    assert (speckit_dir / "index.md").exists()
    assert (speckit_dir / "manifest.yml").exists()
    for filename in ("spec.md", "plan.md", "research.md", "data-model.md", "quickstart.md", "tasks.md"):
        assert (speckit_feature_dir / filename).exists()
    assert (speckit_feature_dir / "contracts" / "README.md").exists()
    assert "Feature Specification: Spec Work" in (speckit_feature_dir / "spec.md").read_text(encoding="utf-8")
    assert "NEEDS CLARIFICATION" in (speckit_feature_dir / "plan.md").read_text(encoding="utf-8")

    result = runner.invoke(app, ["spec", "export-status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHANGE-001  generic  exported  Spec Work" in result.output
    assert "CHANGE-001  openspec  exported  Spec Work" in result.output
    assert "CHANGE-001  speckit  exported  Spec Work" in result.output

    result = runner.invoke(
        app,
        ["spec", "export-show", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "OpenSpec Export - CHANGE-001 - Spec Work" in result.output

    result = runner.invoke(
        app,
        ["spec", "export-show", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Spec Kit Export - CHANGE-001 - Spec Work" in result.output

    for target in ("generic", "openspec", "speckit"):
        result = runner.invoke(
            app,
            ["spec", "export-validate", "CHANGE-001", "--target", target, "--root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Software spec export valid" in result.output
        assert f"target: {target}" in result.output

    (openspec_dir / "spec.md").unlink()
    result = runner.invoke(
        app,
        ["spec", "export-validate", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Missing required software spec export artifact: spec.md" in result.output

    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)])
    (openspec_dir / "manifest.yml").write_text(
        "source:\n  change: CHANGE-999\ntarget: openspec\nartifacts: []\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["spec", "export-validate", "CHANGE-001", "--target", "openspec", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Invalid export manifest: source.change must be CHANGE-001" in result.output

    result = runner.invoke(
        app,
        ["spec", "export", "--change", "CHANGE-001", "--target", "unknown", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Unsupported software spec export target: unknown" in result.output


def test_cli_work_plan_list_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work",
            "--problem",
            "Need invisible Git handoff.",
            "--proposal",
            "Create a P2P Work manifest.",
            "--acceptance",
            "Work manifest exists.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["proposal", "accept", "PROP-001", "--reason", "Ready for handoff.", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Software spec export not found" in result.output

    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Work plan created" in result.output
    assert "work: WORK-001" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    assert manifest.exists()
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "visibility: internal_git" in manifest_text
    assert "auto_branch: false" in manifest_text
    assert "auto_commit: false" in manifest_text
    assert "auto_merge: false" in manifest_text
    assert "export_validated: true" in manifest_text

    result = runner.invoke(app, ["work", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001  planned  CHANGE-001  speckit" in result.output

    result = runner.invoke(app, ["work", "show", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-001 - planned" in result.output
    assert "managed_branch_candidate" in result.output


def test_cli_work_branch_creates_managed_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Branch",
            "--problem",
            "Need an isolated implementation branch.",
            "--proposal",
            "Create a managed branch from a Work manifest.",
            "--acceptance",
            "The Work item is marked branched.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work branch created" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "commits: disabled" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "p2p/work/work-001-change-001-speckit"

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: branched" in manifest_text
    assert "mode: managed_branch" in manifest_text
    assert "current_branch: p2p/work/work-001-change-001-speckit" in manifest_text
    assert "head_commit:" in manifest_text
    assert "base_commit:" in manifest_text


def test_cli_work_branch_requires_clean_worktree(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Branch",
            "--problem",
            "Need an isolated implementation branch.",
            "--proposal",
            "Create a managed branch from a Work manifest.",
            "--acceptance",
            "The Work item is marked branched.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    (tmp_path / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

    result = runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Cannot create managed work branch with uncommitted changes" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"


def test_cli_work_submit_creates_local_commit(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Submit",
            "--problem",
            "Need a local submit commit.",
            "--proposal",
            "Submit managed branch work as a commit.",
            "--acceptance",
            "The Work item is submitted.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])

    feature_file = tmp_path / "feature.txt"
    feature_file.write_text("submitted work\n", encoding="utf-8")

    result = runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work submitted" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "changed_files: 1" in result.output
    assert "feature.txt" in result.output
    assert "push: disabled" in result.output

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: submitted" in manifest_text
    assert "mode: managed_submit" in manifest_text
    assert "pushed: false" in manifest_text
    assert "merged: false" in manifest_text
    assert "feature.txt" in manifest_text
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P submit WORK-001: CHANGE-001"


def test_cli_work_submit_requires_non_manifest_changes(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Submit",
            "--problem",
            "Need a local submit commit.",
            "--proposal",
            "Submit managed branch work as a commit.",
            "--acceptance",
            "The Work item is submitted.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Cannot submit managed work with only Work manifest changes" in result.output


def test_cli_work_review_requests_local_review(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Review",
            "--problem",
            "Need a local review request.",
            "--proposal",
            "Request owner review for submitted work.",
            "--acceptance",
            "The Work item is review_requested.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("submitted work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    review_commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    result = runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work review requested" in result.output
    assert f"review_commit: {review_commit}" in result.output
    assert "pull_request: disabled" in result.output
    assert "merge: owner-controlled" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P review WORK-001"

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: review_requested" in manifest_text
    assert "mode: managed_review" in manifest_text
    assert f"review_commit: {review_commit}" in manifest_text
    assert "pull_request: null" in manifest_text
    assert "merged: false" in manifest_text


def test_cli_work_review_requires_submitted_clean_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Review",
            "--problem",
            "Need a local review request.",
            "--proposal",
            "Request owner review for submitted work.",
            "--acceptance",
            "The Work item is review_requested.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be submitted before review" in result.output

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("submitted work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    result = runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Cannot request managed work review with uncommitted changes" in result.output


def test_cli_work_publish_pushes_reviewed_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Publish",
            "--problem",
            "Need a remote handoff.",
            "--proposal",
            "Publish reviewed work to origin.",
            "--acceptance",
            "The Work branch is pushed.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("published work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work published" in result.output
    assert "branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "remote: origin" in result.output
    assert "pull_request: disabled" in result.output
    assert "merge: owner-controlled" in result.output
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P publish WORK-001"

    remote_branch = _git(
        tmp_path,
        "ls-remote",
        "--heads",
        "origin",
        "p2p/work/work-001-change-001-speckit",
    ).stdout
    assert "refs/heads/p2p/work/work-001-change-001-speckit" in remote_branch

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: published" in manifest_text
    assert "mode: managed_publish" in manifest_text
    assert "remote_branch: p2p/work/work-001-change-001-speckit" in manifest_text
    assert "pull_request: null" in manifest_text
    assert "merged: false" in manifest_text


def test_cli_work_publish_requires_review_and_remote(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Publish",
            "--problem",
            "Need a remote handoff.",
            "--proposal",
            "Publish reviewed work to origin.",
            "--acceptance",
            "The Work branch is pushed.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")

    result = runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be review_requested before publish" in result.output

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("published work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Git remote not found: origin" in result.output


def test_cli_work_accept_merges_published_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Accept",
            "--problem",
            "Need owner-controlled merge.",
            "--proposal",
            "Accept published work locally.",
            "--acceptance",
            "The Work branch is merged into main.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    remote_path = tmp_path.parent / f"{tmp_path.name}.git"
    _git(tmp_path, "init", "--bare", str(remote_path))
    _git(tmp_path, "remote", "add", "origin", str(remote_path))

    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("accepted work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "publish", "WORK-001", "--root", str(tmp_path)])
    _git(tmp_path, "checkout", "main")

    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Managed work accepted" in result.output
    assert "source_branch: p2p/work/work-001-change-001-speckit" in result.output
    assert "merged_into: main" in result.output
    assert "push: disabled" in result.output
    assert "cleanup: disabled" in result.output
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "main"
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
    assert _git(tmp_path, "log", "-1", "--pretty=%s").stdout.strip() == "P2P accept WORK-001"
    assert (tmp_path / "feature.txt").read_text(encoding="utf-8") == "accepted work\n"

    manifest = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "status: accepted" in manifest_text
    assert "mode: managed_accept" in manifest_text
    assert "source_branch: p2p/work/work-001-change-001-speckit" in manifest_text
    assert "merged_into: main" in manifest_text
    assert "pushed: false" in manifest_text
    assert "cleanup: false" in manifest_text


def test_cli_work_accept_requires_published_base_branch(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Managed Work Accept",
            "--problem",
            "Need owner-controlled merge.",
            "--proposal",
            "Accept published work locally.",
            "--acceptance",
            "The Work branch is merged into main.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "refresh", "--change", "CHANGE-001", "--root", str(tmp_path)])
    runner.invoke(app, ["spec", "export", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "plan", "--change", "CHANGE-001", "--target", "speckit", "--root", str(tmp_path)])

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")
    _git(tmp_path, "branch", "-M", "main")
    runner.invoke(app, ["work", "branch", "WORK-001", "--root", str(tmp_path)])
    (tmp_path / "feature.txt").write_text("reviewed work\n", encoding="utf-8")
    runner.invoke(app, ["work", "submit", "WORK-001", "--root", str(tmp_path)])
    runner.invoke(app, ["work", "review", "WORK-001", "--root", str(tmp_path)])

    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "expected base branch main" in result.output

    _git(tmp_path, "checkout", "main")
    result = runner.invoke(app, ["work", "accept", "WORK-001", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Work item must be published before accept" in result.output


def test_cli_work_scan_reads_local_branch_without_checkout(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    _git(tmp_path, "init")
    _git(tmp_path, "add", ".p2p/project.yml")
    _git(tmp_path, "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "init")
    _git(tmp_path, "branch", "-M", "main")

    _git(tmp_path, "checkout", "-b", "p2p/work/work-999-change-001-speckit")
    manifest_dir = tmp_path / ".p2p" / "work" / "WORK-999"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yml").write_text(
        "work_id: WORK-999\n"
        "status: planned\n"
        "source:\n"
        "  change: CHANGE-001\n"
        "handoff:\n"
        "  target: speckit\n"
        "git:\n"
        "  branch_name: p2p/work/work-999-change-001-speckit\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", ".p2p/work/WORK-999/manifest.yml")
    _git(
        tmp_path,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test User",
        "commit",
        "-m",
        "add work manifest",
    )
    _git(tmp_path, "checkout", "main")

    result = runner.invoke(app, ["work", "scan", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "branches: 1" in result.output
    assert "work_items: 1" in result.output
    assert "WORK-999  planned  CHANGE-001  speckit  p2p/work/work-999-change-001-speckit" in result.output

    work_registry = tmp_path / ".p2p" / "registries" / "work.yml"
    assert work_registry.exists()
    registry_text = work_registry.read_text(encoding="utf-8")
    assert "WORK-999" in registry_text
    assert "p2p/work/work-999-change-001-speckit" in registry_text

    result = runner.invoke(app, ["work", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "WORK-999  planned  CHANGE-001  speckit" in result.output


def test_cli_registry_includes_choice_artifacts(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    choice_dir = tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy"
    choice_dir.mkdir(parents=True)
    (choice_dir / "choice.md").write_text(
        "---\n"
        "choice_id: CHOICE-001\n"
        "title: Initial AI Strategy\n"
        "status: open\n"
        "---\n\n"
        "# CHOICE-001 - Initial AI Strategy\n",
        encoding="utf-8",
    )
    (choice_dir / "options.yml").write_text(
        "options:\n"
        "  - id: A\n"
        "    title: Prompt-only first\n"
        "  - id: B\n"
        "    title: Direct AI now\n",
        encoding="utf-8",
    )
    (choice_dir / "decision.md").write_text(
        "# Decision - CHOICE-001\n\n## Selected Option\n\nPending.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    assert result.exit_code == 0

    result = runner.invoke(app, ["registry", "show", "choices", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001" in result.output
    assert "Initial AI Strategy" in result.output


def test_cli_choice_create_list_and_decide(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Prompt Workflow", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Initial AI Strategy",
            "--option",
            "Prompt-only first",
            "--option",
            "Direct AI now",
            "--option",
            "Prompt-only first, AI adapter later",
            "--related",
            "PROP-001",
            "--source",
            "INTAKE-001",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice created" in result.output
    assert "id: CHOICE-001" in result.output

    choice_dir = tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy"
    assert (choice_dir / "choice.md").exists()
    assert "Prompt-only first" in (choice_dir / "options.yml").read_text(encoding="utf-8")

    result = runner.invoke(app, ["choice", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001  open  Initial AI Strategy" in result.output

    result = runner.invoke(
        app,
        [
            "choice",
            "decide",
            "CHOICE-001",
            "--option",
            "C",
            "--reason",
            "Keep MVP stable while planning adapters.",
            "--decider",
            "owner",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice decided" in result.output
    assert "selected: C - Prompt-only first, AI adapter later" in result.output

    result = runner.invoke(app, ["choice", "list", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001  decided  Initial AI Strategy" in result.output
    assert "C - Prompt-only first, AI adapter" in result.output

    decision = (choice_dir / "decision.md").read_text(encoding="utf-8")
    assert "`decided`" in decision
    assert "Keep MVP stable while planning adapters." in decision

    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["registry", "show", "choices", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "CHOICE-001" in result.output


def test_cli_choice_discovery_blocking_and_next_integration(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Governance Model", "--root", str(tmp_path)])
    runner.invoke(app, ["vote", "record", "PROP-001", "--choice", "A", "--reason", "Prefer A", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Needed.", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "create", "--from", "PROP-001", "--title", "Governance Model", "--root", str(tmp_path)])
    runner.invoke(app, ["change", "set-status", "CHANGE-001", "planned", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "choice",
            "create",
            "--title",
            "Governance Scope",
            "--option",
            "Minimal governance",
            "--option",
            "Full governance",
            "--related",
            "PROP-001",
            "--root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["choice", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "project choices:" in result.output
    assert "CHOICE-001  open  Governance Scope" in result.output
    assert "proposal-local candidates:" in result.output
    assert "CHOICE-PROP-001" in result.output

    result = runner.invoke(app, ["choice", "discover", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "proposal_local_choice_candidate" in result.output
    assert "CHOICE-PROP-001" in result.output
    assert "open_project_choice" in result.output

    result = runner.invoke(
        app,
        [
            "choice",
            "block",
            "CHOICE-001",
            "--change",
            "CHANGE-001",
            "--reason",
            "Governance scope must be decided first.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Choice blocker recorded" in result.output

    result = runner.invoke(app, ["choice", "show", "CHOICE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "blocks:" in result.output
    assert "change CHANGE-001  active" in result.output
    assert "Governance scope must be decided first." in result.output

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-BLOCKER-001  high  resolve_choice" in result.output
    assert "target: CHOICE-001" in result.output

    result = runner.invoke(
        app,
        ["choice", "unblock", "CHOICE-001", "--change", "CHANGE-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Choice blocker cleared" in result.output

    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "continue_change" in result.output
    assert "target: CHANGE-001" in result.output


def test_cli_intake_prompt_import_and_status(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "CLI Foundation", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "decision",
            "record",
            "PROP-001",
            "--outcome",
            "accepted",
            "--reason",
            "Baseline CLI work.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "intake",
            "prompt",
            "La CLI dovrebbe integrare subito Codex",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Intake prompt created" in result.output
    assert "id: INTAKE-001" in result.output

    intake_dir = tmp_path / ".p2p" / "intake" / "INTAKE-001"
    prompt = (intake_dir / "intake.prompt.md").read_text(encoding="utf-8")
    assert "P2P Intake Prompt" in prompt
    assert "La CLI dovrebbe integrare subito Codex" in prompt
    assert "PROP-001" in prompt
    assert "Do not accept, reject, defer, merge or supersede proposals" in prompt

    result = runner.invoke(app, ["intake", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "INTAKE-001  pending" in result.output

    output_dir = tmp_path / "intake-output"
    output_dir.mkdir()
    (output_dir / "recommendation.md").write_text(
        "# Recommendation\n\nClassify as alternative to PROP-001.\n",
        encoding="utf-8",
    )
    (output_dir / "related-proposals.yml").write_text(
        "related_proposals:\n"
        "  - proposal: PROP-001\n"
        "    relationship: alternative_to\n"
        "    rationale: Changes initial AI strategy.\n",
        encoding="utf-8",
    )
    (output_dir / "suggested-actions.yml").write_text(
        "suggested_actions:\n"
        "  - type: add_contribution\n"
        "    target: PROP-001\n"
        "    rationale: Treat as alternative implementation path.\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["intake", "import", "INTAKE-001", str(output_dir), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Intake imported" in result.output
    assert "suggested-actions.yml" in result.output

    result = runner.invoke(app, ["intake", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "INTAKE-001  analyzed" in result.output

    decision = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-cli-foundation" / "decision.md"
    ).read_text(encoding="utf-8")
    assert "Baseline CLI work." in decision


def test_cli_intake_apply_plan_show_and_run(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Prompt Workflow", "--root", str(tmp_path)])
    intake_dir = tmp_path / ".p2p" / "intake" / "INTAKE-001"
    intake_dir.mkdir(parents=True)
    (intake_dir / "recommendation.md").write_text("# Recommendation\n\nAnalyze direct AI.\n", encoding="utf-8")
    (intake_dir / "related-proposals.yml").write_text("related_proposals: []\n", encoding="utf-8")
    (intake_dir / "suggested-actions.yml").write_text(
        "suggested_actions:\n"
        "  - type: add_contribution\n"
        "    target: PROP-001\n"
        "    rationale: Preserve direct AI as a tracked alternative.\n"
        "  - type: open_choice\n"
        "    target: PROP-001\n"
        "    rationale: Decide whether direct AI belongs in this workflow.\n"
        "  - type: defer\n"
        "    target: PROP-001\n"
        "    rationale: Governance decision preview only.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["intake", "apply", "plan", "INTAKE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Intake apply plan created" in result.output
    assert "actions: 3" in result.output

    result = runner.invoke(app, ["intake", "apply", "show", "INTAKE-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "APPLY-001  pending  supported  add_contribution -> PROP-001" in result.output
    assert "APPLY-002  pending  requires_input  open_choice -> PROP-001" in result.output
    assert "APPLY-003  pending  governance_only  defer -> PROP-001" in result.output

    result = runner.invoke(
        app,
        ["intake", "apply", "run", "INTAKE-001", "--action", "APPLY-001", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Intake apply action applied" in result.output
    assert "type: add_contribution" in result.output

    contributions = (
        tmp_path / ".p2p" / "proposals" / "PROP-001-prompt-workflow" / "contributions.yml"
    ).read_text(encoding="utf-8")
    assert "Preserve direct AI as a tracked alternative." in contributions
    assert "intake:INTAKE-001" in contributions

    result = runner.invoke(
        app,
        ["intake", "apply", "run", "INTAKE-001", "--action", "APPLY-002", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "requires at least two --option values" in result.output

    result = runner.invoke(
        app,
        [
            "intake",
            "apply",
            "run",
            "INTAKE-001",
            "--action",
            "APPLY-002",
            "--option",
            "Keep prompt-only",
            "--option",
            "Explore direct AI",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "type: open_choice" in result.output
    assert (tmp_path / ".p2p" / "choices" / "CHOICE-001-intake-intake-001-choice-for-prop-001").exists()

    result = runner.invoke(
        app,
        ["intake", "apply", "run", "INTAKE-001", "--action", "APPLY-003", "--root", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "governance_only" in result.output

    applied = (intake_dir / "applied-actions.yml").read_text(encoding="utf-8")
    assert "APPLIED-001" in applied
    assert "APPLIED-002" in applied
    assert "add_contribution" in applied
    assert "open_choice" in applied

    plan = (intake_dir / "apply-plan.yml").read_text(encoding="utf-8")
    assert "status: applied" in plan
    assert "created_choice: CHOICE-001" in plan


def test_cli_project_brief_prompt_import_and_show(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "CLI Foundation", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Baseline CLI work.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["project", "refresh", "--root", str(tmp_path)])
    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])

    result = runner.invoke(app, ["project", "brief", "prompt", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project brief prompt created" in result.output
    assert "brief.prompt.md" in result.output

    project_dir = tmp_path / ".p2p" / "project"
    prompt = (project_dir / "brief.prompt.md").read_text(encoding="utf-8")
    context = (project_dir / "brief-context.md").read_text(encoding="utf-8")
    assert "P2P Operational Brief Prompt" in prompt
    assert "Do not accept, reject, defer, merge, supersede, or apply recommendations" in prompt
    assert "CLI Foundation" in context
    assert "## Proposals Registry" in context

    output_dir = tmp_path / "brief-output"
    output_dir.mkdir()
    (output_dir / "operational-brief.md").write_text(
        "# Operational Brief\n\n## Where We Are\n\nThe CLI foundation is accepted.\n",
        encoding="utf-8",
    )
    (output_dir / "next-actions.yml").write_text(
        "next_actions:\n"
        "  - id: NEXT-001\n"
        "    priority: high\n"
        "    kind: create_change\n"
        "    target: PROP-001\n"
        "    reason: Accepted proposal needs operational packaging.\n"
        "    command: p2p change create --from PROP-001\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["project", "brief", "import", str(output_dir), "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "Project brief imported" in result.output
    assert "operational-brief.md" in result.output
    assert "next-actions.yml" in result.output

    result = runner.invoke(app, ["project", "brief", "show", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "The CLI foundation is accepted." in result.output

    result = runner.invoke(app, ["next", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Next actions" in result.output
    assert "NEXT-001  high  create_change" in result.output
    assert "p2p change create --from PROP-001" in result.output
    assert ".p2p/project/next-actions.yml" in result.output

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-001  high  create_change" in result.output

    result = runner.invoke(app, ["project", "status", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "operational:" in result.output
    assert "brief: available" in result.output
    assert "next actions: 1" in result.output
    assert "first next: NEXT-001 high create_change PROP-001" in result.output


def test_cli_next_falls_back_without_imported_next_actions(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Demo Project", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Managed Git", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "accept",
            "PROP-001",
            "--reason",
            "Needed for collaboration.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        ["change", "create", "--from", "PROP-001", "--title", "Managed Git", "--root", str(tmp_path)],
    )
    runner.invoke(app, ["change", "set-status", "CHANGE-001", "planned", "--root", str(tmp_path)])

    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-FALLBACK-001  high  refresh_registry" in result.output
    assert "p2p registry refresh" in result.output

    runner.invoke(app, ["registry", "refresh", "--root", str(tmp_path)])
    result = runner.invoke(app, ["next", "--top", "1", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "NEXT-FALLBACK-001  high  continue_change" in result.output
    assert "target: CHANGE-001" in result.output
    assert "p2p change tasks CHANGE-001" in result.output
    assert "source: fallback" in result.output
