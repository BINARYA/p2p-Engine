from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.decision_context_fixtures import project_files


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project")
    return workspace


def _write_suggested_actions(intake_dir: Path) -> None:
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


def test_intake_lifecycle_service_creates_prompt_and_status(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._intake_lifecycle_service()

    prompt = service.create_prompt("La CLI dovrebbe integrare subito Codex")
    statuses = service.statuses()

    assert prompt.intake_id == "INTAKE-001"
    assert prompt.prompt_path == Path(".p2p/intake/INTAKE-001/intake.prompt.md")
    assert statuses[0].status == "pending"
    prompt_text = (tmp_path / ".p2p" / "intake" / "INTAKE-001" / "intake.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "Do not accept, reject, defer, merge or supersede proposals" in prompt_text


def test_intake_uses_relevant_idea_context_without_first_n_or_writeback(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    for number in range(1, 31):
        workspace.create_proposal_with_details(
            f"Unrelated low identifier {number}",
            problem=f"Routine archival concern {number}.",
            proposal=f"Keep archival workflow {number} unchanged.",
        )
    relevant = workspace.create_proposal_with_details(
        "Quasar decision retrieval",
        problem="Quasar decisions disappear from intake context.",
        goals=["Preserve quasar constraints."],
        proposal="Retrieve quasar decisions by semantic proximity.",
    )
    workspace.record_decision(
        relevant.proposal_id,
        DecisionOutcome.accepted,
        "Quasar retrieval is the accepted constraint.",
        "owner",
    )
    before = project_files(tmp_path)

    prompt = workspace._intake_lifecycle_service().create_prompt(
        "Quasar retrieval"
    )

    after = project_files(tmp_path)
    context = (tmp_path / prompt.path / "context.md").read_text(encoding="utf-8")
    changed = {
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    }
    assert relevant.proposal_id == "PROP-031"
    assert "### PROP-031" in context
    assert "Quasar retrieval is the accepted constraint." in context
    assert "PROP-001: draft" not in context
    assert "## Registry Status" in context
    assert changed
    assert all(path.startswith(".p2p/intake/INTAKE-001/") for path in changed)
    assert not (tmp_path / ".p2p" / "choices").exists()


def test_intake_generic_idea_returns_explicit_empty_context(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("A proposal that must not be selected by position")

    prompt = workspace._intake_lifecycle_service().create_prompt("the e di and")

    context = (tmp_path / prompt.path / "context.md").read_text(encoding="utf-8")
    assert "No nearby context was selected: no_meaningful_query_tokens." in context
    assert "### PROP-001" not in context


def test_intake_lifecycle_service_imports_directory_and_file(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._intake_lifecycle_service()
    service.create_prompt("A new idea.")
    output_dir = tmp_path / "intake-output"
    output_dir.mkdir()
    (output_dir / "recommendation.md").write_text("# Recommendation\n\nAnalyze direct AI.\n", encoding="utf-8")
    (output_dir / "related-proposals.yml").write_text("related_proposals: []\n", encoding="utf-8")
    (output_dir / "suggested-actions.yml").write_text("suggested_actions: []\n", encoding="utf-8")

    imported = service.import_output("INTAKE-001", output_dir)
    statuses = service.statuses()
    file_source = tmp_path / "recommendation.md"
    file_source.write_text("# Recommendation\n\nSingle-file import.\n", encoding="utf-8")
    imported_file = service.import_output("INTAKE-001", file_source)

    assert Path(".p2p/intake/INTAKE-001/suggested-actions.yml") in imported
    assert statuses[0].status == "analyzed"
    assert imported_file == [Path(".p2p/intake/INTAKE-001/recommendation.md")]


def test_intake_lifecycle_service_creates_and_shows_apply_plan(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Prompt Workflow")
    service = workspace._intake_lifecycle_service()
    intake_dir = tmp_path / ".p2p" / "intake" / "INTAKE-001"
    intake_dir.mkdir(parents=True)
    _write_suggested_actions(intake_dir)

    plan = service.create_apply_plan("INTAKE-001")
    shown = service.show_apply_plan("INTAKE-001")

    assert [action["support"] for action in plan.actions] == [
        "supported",
        "requires_input",
        "governance_only",
    ]
    assert shown.actions[1]["required_inputs"] == ["option", "option"]


def test_intake_lifecycle_service_runs_supported_actions(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Prompt Workflow")
    service = workspace._intake_lifecycle_service()
    intake_dir = tmp_path / ".p2p" / "intake" / "INTAKE-001"
    intake_dir.mkdir(parents=True)
    _write_suggested_actions(intake_dir)
    service.create_apply_plan("INTAKE-001")

    contribution = service.run_apply_action("INTAKE-001", "APPLY-001")
    choice = service.run_apply_action(
        "INTAKE-001",
        "APPLY-002",
        options=["Keep prompt-only", "Explore direct AI"],
    )

    assert contribution.action_type == "add_contribution"
    assert choice.action_type == "open_choice"
    assert (tmp_path / ".p2p" / "choices" / "CHOICE-001-intake-intake-001-choice-for-prop-001").exists()
    applied = yaml.safe_load((intake_dir / "applied-actions.yml").read_text(encoding="utf-8"))
    assert [record["type"] for record in applied["applied_actions"]] == ["add_contribution", "open_choice"]


def test_intake_lifecycle_service_validates_error_paths(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Prompt Workflow")
    service = workspace._intake_lifecycle_service()
    intake_dir = tmp_path / ".p2p" / "intake" / "INTAKE-001"
    intake_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="Intake source not found"):
        service.import_output("INTAKE-001", tmp_path / "missing")

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="No intake artifacts found"):
        service.import_output("INTAKE-001", empty_dir)

    (intake_dir / "suggested-actions.yml").write_text("suggested_actions: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="suggested_actions` list"):
        service.create_apply_plan("INTAKE-001")

    _write_suggested_actions(intake_dir)
    with pytest.raises(ValueError, match="apply plan not found"):
        service.show_apply_plan("INTAKE-001")

    service.create_apply_plan("INTAKE-001")
    with pytest.raises(ValueError, match="Apply action not found"):
        service.run_apply_action("INTAKE-001", "APPLY-999")
    with pytest.raises(ValueError, match="requires at least two --option values"):
        service.run_apply_action("INTAKE-001", "APPLY-002")
    with pytest.raises(ValueError, match="governance_only"):
        service.run_apply_action("INTAKE-001", "APPLY-003")

    applied_path = intake_dir / "applied-actions.yml"
    applied_path.write_text("applied_actions: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="applied_actions` list"):
        service.run_apply_action("INTAKE-001", "APPLY-001")
