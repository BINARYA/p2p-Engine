from __future__ import annotations

import hashlib
from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.contribution import ContributionType
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_artifact_state import ProposalArtifactStatus
from p2p_engine.core.proposal_questions import ProposalQuestionPriority
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error
from tests.proposal_decision_fixtures import record_decision


runner = CliRunner()


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _initialized_workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Proposal Read Contract", owner="owner", vertical_id="base_project")
    return workspace


def test_proposal_list_json_handles_empty_project_without_writes(tmp_path: Path) -> None:
    _initialized_workspace(tmp_path)
    before = _hash_tree(tmp_path)

    result = runner.invoke(
        app,
        ["proposal", "list", "--format", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    payload = cli_data(result, operation="proposal.list")["proposal_list"]
    assert payload["contract_version"] == "p2p-proposal-list/v1"
    assert payload["total"] == 0
    assert payload["returned"] == 0
    assert payload["items"] == []
    assert payload["counts"]["filtered"]["by_status"] == {}
    assert _hash_tree(tmp_path) == before


def test_proposal_list_json_filters_and_paginates_by_decision_state(tmp_path: Path) -> None:
    workspace = _initialized_workspace(tmp_path)
    accepted = workspace.create_proposal_with_details(
        title="Accepted proposal",
        problem="The owner needs a committed proposal.",
        proposal="Accept this proposal.",
    )
    draft = workspace.create_proposal_with_details(
        title="Draft proposal",
        problem="The owner also needs a pending proposal.",
        proposal="Keep this proposal draft.",
    )
    record_decision(
        workspace,
        accepted.proposal_id,
        DecisionOutcome.accepted,
        "Owner accepted it.",
        "owner",
    )

    result = runner.invoke(
        app,
        [
            "proposal",
            "list",
            "--decision-state",
            "accepted",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = cli_data(result, operation="proposal.list")["proposal_list"]
    assert payload["filters"] == {"status": None, "decision_state": "accepted"}
    assert payload["total"] == 1
    assert payload["items"][0]["proposal_id"] == accepted.proposal_id
    assert payload["items"][0]["decision_state"] == "accepted"
    assert payload["counts"]["unfiltered"]["by_effective_state"]["accepted"] == 1
    assert payload["counts"]["unfiltered"]["by_effective_state"]["undecided"] == 1

    paged = runner.invoke(
        app,
        [
            "proposal",
            "list",
            "--status",
            "draft",
            "--limit",
            "1",
            "--offset",
            "0",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert paged.exit_code == 0, paged.output
    page = cli_data(paged, operation="proposal.list")["proposal_list"]
    assert page["total"] == 1
    assert page["items"][0]["proposal_id"] == draft.proposal_id


def test_proposal_show_json_reports_missing_proposal_with_stable_error(tmp_path: Path) -> None:
    _initialized_workspace(tmp_path)

    result = runner.invoke(
        app,
        ["proposal", "show", "PROP-999", "--format", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="proposal.show")
    assert error["code"] == "P2P_PROPOSAL_NOT_FOUND"
    assert "PROP-999" in error["message"]


def test_proposal_show_json_returns_full_detail_readiness_artifacts_and_contribution_groups(
    tmp_path: Path,
) -> None:
    workspace = _initialized_workspace(tmp_path)
    proposal = workspace.create_proposal_with_details(
        title="Detailed proposal",
        problem="WaveKit needs a proposal detail contract.",
        context="The server reads project memory through the CLI.",
        goals=["Expose a typed detail view."],
        non_goals=["Mutate data from the read command."],
        proposal="Return full proposal detail as JSON.",
        acceptance_criteria=["Readiness, artifacts and contributions are visible."],
    )
    workspace.add_contribution(
        proposal.proposal_id,
        ContributionType.suggestion,
        text="Expose suggestions as structured contribution records.",
        relevance_hint="ui",
        author="supporter",
    )
    workspace.add_contribution(
        proposal.proposal_id,
        ContributionType.finding,
        text="The current Angular page needs contribution grouping.",
        relevance_hint="backend",
        author="codex",
    )
    workspace.add_contribution(
        proposal.proposal_id,
        ContributionType.open_question,
        text="Should owners see open questions separately?",
        relevance_hint="owner",
        author="supporter",
    )
    workspace.add_proposal_question(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Which owner decision is still missing?",
        priority=ProposalQuestionPriority.high,
        rationale="The proposal is not decision-ready without owner input.",
        actor="codex",
    )
    workspace.write_proposal_readiness(
        proposal.proposal_id,
        {
            "status": "assessed",
            "profile_id": "default-readiness-v0.1",
            "profile_version": "0.1",
            "computed_score": 68,
            "computed_label": "weak",
            "confidence": "low",
            "failed_gates": ["owner_questions_resolution"],
            "missing": ["owner_questions_resolution"],
            "suggested_next": ["p2p proposal questions next PROP-001"],
            "criteria": {},
        },
    )
    workspace.set_proposal_artifact_state(
        proposal.proposal_id,
        "impact_map",
        status=ProposalArtifactStatus.not_applicable,
        reason="No cross-proposal impact in this fixture.",
        actor="codex",
    )
    before = _hash_tree(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "show",
            proposal.proposal_id,
            "--limit",
            "2",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    detail = cli_data(result, operation="proposal.show")["proposal_detail"]
    assert detail["contract_version"] == "p2p-proposal-detail/v1"
    assert detail["proposal_id"] == proposal.proposal_id
    assert detail["core_sections"]["problem"] == "WaveKit needs a proposal detail contract."
    assert detail["readiness"]["status"] == "assessed"
    assert detail["readiness"]["computed_score"] == 68
    assert detail["artifact_state"]["counts_by_status"]["not_applicable"] == 1
    assert detail["contributions"]["total"] == 3
    assert detail["contributions"]["returned"] == 2
    assert detail["contributions"]["truncated"] is True
    assert detail["contributions"]["counts_by_type"]["suggestion"] == 1
    assert detail["contributions"]["counts_by_type"]["finding"] == 1
    assert detail["contributions"]["counts_by_type"]["open_question"] == 1
    assert detail["contributions"]["groups"]["suggestion"]["items"][0]["author"] == "supporter"
    assert detail["questions"]["owner_questions"]["total"] == 1
    assert detail["questions"]["analytical_open_questions"]["total"] == 1
    assert "p2p proposal questions next PROP-001" in detail["next_actions"]
    assert _hash_tree(tmp_path) == before


def test_proposal_show_json_stabilizes_uninitialized_readiness_and_question_shapes(
    tmp_path: Path,
) -> None:
    workspace = _initialized_workspace(tmp_path)
    proposal = workspace.create_proposal_with_details(
        title="Initial proposal shape",
        problem="WaveKit renders proposal detail before analysis starts.",
        proposal="Return typed empty readiness and question sections.",
    )

    result = runner.invoke(
        app,
        [
            "proposal",
            "show",
            proposal.proposal_id,
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    detail = cli_data(result, operation="proposal.show")["proposal_detail"]
    readiness = dict(detail["readiness"])
    assert str(readiness.pop("path")).endswith("/readiness.yml")
    assert readiness == {
        "proposal_id": proposal.proposal_id,
        "status": "not_assessed",
        "profile_id": None,
        "profile_version": None,
        "computed_score": None,
        "computed_label": None,
        "confidence": None,
        "failed_gates": [],
        "missing": [],
        "suggested_next": [f"p2p proposal readiness init {proposal.proposal_id}"],
        "owner_question_state": {},
    }
    questions = dict(detail["questions"])
    assert str(questions.pop("path")).endswith("/questions.yml")
    assert questions == {
        "proposal_id": proposal.proposal_id,
        "status": "not_initialized",
        "owner_questions": {
            "total": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
        },
        "analytical_open_questions": {
            "total": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
        },
        "narrative_question_artifacts": {
            "total": 0,
            "returned": 0,
            "truncated": False,
            "items": [],
        },
    }
