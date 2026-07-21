from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


runner = CliRunner()


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _software_workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Progress",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal = workspace.create_proposal_with_details(
        "Data model evidence",
        problem="Domain entities and state lifecycle need a data model.",
        proposal="Define domain entities, data model, and state lifecycle.",
    )
    return workspace, proposal.proposal_id


def test_progress_is_read_only_and_axes_are_independent(tmp_path: Path) -> None:
    workspace, proposal_id = _software_workspace(tmp_path)
    before = _hash_tree(tmp_path)

    progress = workspace.project_progress(include_heuristics=True)

    assert _hash_tree(tmp_path) == before
    assert progress.definition.status == "measured"
    assert progress.definition.ratio.percentage == 0.0
    assert progress.evidence.ratio.numerator == 0
    data_model = next(item for item in progress.sections if item.section_id == "data_model")
    assert proposal_id in data_model.heuristic_proposals
    assert not data_model.declared_committed_proposals
    assert progress.question_counts["to_answer"] > 0

    fast_progress = workspace.project_progress()
    assert all(not section.heuristic_proposals for section in fast_progress.sections)
    assert fast_progress.evidence.ratio.exclusions["heuristics_not_requested"] == 1


def test_question_lifecycle_counts_do_not_change_progress_percentages(tmp_path: Path) -> None:
    workspace, _ = _software_workspace(tmp_path)
    before = workspace.project_progress()
    question = workspace.next_project_question()
    assert question is not None

    workspace.answer_project_question(
        question.question_id,
        values={"value": "Owner answer"},
        actor="owner",
        expected_revision=question.revision,
    )
    after = workspace.project_progress()

    assert after.definition.ratio == before.definition.ratio
    assert after.evidence.ratio == before.evidence.ratio
    assert after.question_counts["answered"] == 1


def test_progress_reports_residual_sections_without_safe_active_question(tmp_path: Path) -> None:
    workspace, _ = _software_workspace(tmp_path)
    question_service = workspace._project_question_state_service()
    artifact = question_service.read()
    question_service.path.write_bytes(
        question_service.candidate_bytes(replace(artifact, groups=(), questions=()))
    )

    progress = workspace.project_progress()

    assert progress.question_counts["no_safe_question"] > 0
    assert progress.definition.ratio.percentage == 0.0
    assert progress.evidence.ratio.percentage == 0.0


def test_missing_definition_is_not_initialized_without_percentage(tmp_path: Path) -> None:
    workspace, _ = _software_workspace(tmp_path)
    (tmp_path / ".p2p" / "project" / "definition.yml").unlink()

    progress = workspace.project_progress()

    assert progress.definition.status == "not_initialized"
    assert progress.definition.ratio.percentage is None
    assert progress.definition.ratio.denominator == 0


def test_definition_and_committed_declared_evidence_advance_separately(tmp_path: Path) -> None:
    workspace, proposal_id = _software_workspace(tmp_path)
    patch = tmp_path / "definition.yml"
    patch.write_text(
        yaml.safe_dump(
            {
                "project_definition_patch": {
                    "schema_version": 1,
                    "actor": "owner",
                    "operations": [
                        {
                            "op": "set_field",
                            "section_id": "data_model",
                            "field_id": "domain_entities",
                            "value": "Proposal, decision, relation, and derived freshness node.",
                            "provenance": {"source": "owner_answer"},
                        },
                        {"op": "set_section_status", "section_id": "data_model", "status": "complete"},
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    workspace.update_project_definition(patch)
    coverage = {
        "vertical_coverage": {
            "schema_version": 2,
            "proposal_id": proposal_id,
            "vertical_id": "software_project",
            "sections": [
                {
                    "id": "data_model",
                    "relevance": "direct",
                    "rationale": "The accepted proposal defines domain entities.",
                    "source": "owner_review",
                    "provenance": {"evidence": ["proposal.md"]},
                }
            ],
            "provenance": {
                "operation_id": f"proposal-vertical-coverage:{proposal_id}",
                "actor": "owner",
                "authority": "owner_confirmed",
                "source": "owner_review",
            },
        }
    }
    preview = workspace.preview_proposal_vertical_coverage(proposal_id, coverage, actor="owner")
    workspace.apply_proposal_vertical_coverage(
        proposal_id,
        coverage,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    draft_progress = workspace.project_progress()
    draft_data = next(item for item in draft_progress.sections if item.section_id == "data_model")
    assert draft_data.definition_units_complete == 2
    assert draft_data.declared_non_committed_proposals == (proposal_id,)
    assert draft_progress.evidence.ratio.numerator == 0

    record_decision(workspace, proposal_id, DecisionOutcome.accepted, "Defines project evidence.", "owner")
    accepted_progress = workspace.project_progress()
    accepted_data = next(item for item in accepted_progress.sections if item.section_id == "data_model")
    assert accepted_data.declared_committed_proposals == (proposal_id,)
    assert accepted_progress.evidence.ratio.numerator == 1
    assert accepted_progress.definition.ratio.numerator > 0


def test_project_progress_cli_json_matches_service(tmp_path: Path) -> None:
    workspace, _ = _software_workspace(tmp_path)

    result = runner.invoke(app, ["project", "progress", "--format", "json", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["project_progress"]
    progress = workspace.project_progress()
    assert payload["definition"]["ratio"]["numerator"] == progress.definition.ratio.numerator
    assert payload["evidence"]["basis"] == progress.evidence.basis
