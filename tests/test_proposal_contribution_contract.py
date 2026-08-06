from __future__ import annotations

import hashlib
from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.contribution import ContributionType
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error


runner = CliRunner()


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _initialized_workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Contribution Contract", owner="owner", vertical_id="base_project")
    proposal = workspace.create_proposal_with_details(
        title="Contribution target",
        problem="The proposal needs structured feedback.",
        proposal="Record feedback as proposal contributions.",
    )
    return workspace, proposal.proposal_id


def _add_json(
    root: Path,
    proposal_id: str,
    key: str,
    *,
    text: str = "This is a structured suggestion.",
    contribution_type: str = "suggestion",
):
    return runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "add",
            proposal_id,
            text,
            "--type",
            contribution_type,
            "--relevance",
            "high",
            "--author",
            "supporter",
            "--actor",
            "wavekit",
            "--operation-key",
            key,
            "--format",
            "json",
            "--root",
            str(root),
        ],
    )


def test_contribution_list_json_filters_counts_and_declares_review_unsupported(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _initialized_workspace(tmp_path)
    for contribution_type in (
        ContributionType.suggestion,
        ContributionType.objection,
        ContributionType.finding,
        ContributionType.open_question,
        ContributionType.alternative,
    ):
        workspace.add_contribution(
            proposal_id,
            contribution_type,
            text=f"{contribution_type.value} text",
            relevance_hint="medium",
            author="supporter",
        )
    before = _hash_tree(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "list",
            proposal_id,
            "--type",
            "suggestion",
            "--limit",
            "1",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = cli_data(result, operation="proposal.contribution.list")[
        "proposal_contribution_list"
    ]
    assert payload["contract_version"] == "p2p-proposal-contribution-list/v1"
    assert payload["proposal_id"] == proposal_id
    assert payload["filters"] == {"type": "suggestion"}
    assert payload["total"] == 1
    assert payload["returned"] == 1
    assert payload["items"][0]["type"] == "suggestion"
    for contribution_type in (
        "suggestion",
        "objection",
        "finding",
        "open_question",
        "alternative",
    ):
        assert payload["counts"]["unfiltered_by_type"][contribution_type] == 1
    assert payload["review_capability"]["supported"] is False
    assert payload["review_capability"]["code"] == "P2P_CONTRIBUTION_REVIEW_UNSUPPORTED"
    assert _hash_tree(tmp_path) == before


def test_contribution_add_json_writes_receipt_and_replays_without_writes(
    tmp_path: Path,
) -> None:
    _workspace, proposal_id = _initialized_workspace(tmp_path)
    key = "wavekit:123e4567-e89b-12d3-a456-426614174200"

    result = _add_json(tmp_path, proposal_id, key)

    assert result.exit_code == 0, result.output
    data = cli_data(result, operation="proposal.contribution.add")
    created = data["proposal_contribution_add"]
    mutation = data["mutation"]
    assert mutation["status"] == "applied"
    assert mutation["operation_id"] == "proposal.contribution.add"
    assert created["proposal_id"] == proposal_id
    assert created["contribution"]["contribution_id"] == "C001"
    assert created["contribution"]["type"] == "suggestion"
    assert created["review_capability"]["supported"] is False
    status = P2PWorkspace(tmp_path).mutation_status(idempotency_key=key)
    assert status.state == "applied"
    assert status.operation == "proposal_contribution_add"
    assert status.result["contribution"]["contribution_id"] == "C001"
    before = _hash_tree(tmp_path)

    replay = _add_json(tmp_path, proposal_id, key)

    assert replay.exit_code == 0, replay.output
    replay_data = cli_data(replay, operation="proposal.contribution.add")
    assert replay_data["mutation"]["status"] == "already_applied"
    assert replay_data["proposal_contribution_add"]["contribution"] == created["contribution"]
    assert _hash_tree(tmp_path) == before


def test_contribution_add_json_divergent_replay_conflicts_without_writes(
    tmp_path: Path,
) -> None:
    _workspace, proposal_id = _initialized_workspace(tmp_path)
    key = "wavekit:123e4567-e89b-12d3-a456-426614174201"
    first = _add_json(tmp_path, proposal_id, key)
    assert first.exit_code == 0, first.output
    before = _hash_tree(tmp_path)

    conflict = _add_json(
        tmp_path,
        proposal_id,
        key,
        text="A different contribution with the same key.",
    )

    assert conflict.exit_code == 3
    error = cli_error(conflict, operation="proposal.contribution.add")
    assert error["code"] == "P2P_IDEMPOTENCY_CONFLICT"
    assert _hash_tree(tmp_path) == before


def test_contribution_add_json_requires_operation_key(tmp_path: Path) -> None:
    _workspace, proposal_id = _initialized_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "add",
            proposal_id,
            "Missing operation key.",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="proposal.contribution.add")
    assert error["code"] == "P2P_IDEMPOTENCY_KEY_REQUIRED"


def test_contribution_json_rejects_invalid_type_and_missing_proposal_without_writes(
    tmp_path: Path,
) -> None:
    _workspace, proposal_id = _initialized_workspace(tmp_path)
    before = _hash_tree(tmp_path)

    invalid_type = _add_json(
        tmp_path,
        proposal_id,
        "wavekit:123e4567-e89b-12d3-a456-426614174202",
        contribution_type="invalid",
    )

    assert invalid_type.exit_code == 2
    error = cli_error(invalid_type, operation="proposal.contribution.add")
    assert error["code"] == "P2P_CONTRIBUTION_INVALID_TYPE"
    assert _hash_tree(tmp_path) == before

    missing = _add_json(
        tmp_path,
        "PROP-999",
        "wavekit:123e4567-e89b-12d3-a456-426614174203",
    )

    assert missing.exit_code == 2
    error = cli_error(missing, operation="proposal.contribution.add")
    assert error["code"] == "P2P_PROPOSAL_NOT_FOUND"
    assert _hash_tree(tmp_path) == before


def test_contribution_list_json_reports_missing_proposal(tmp_path: Path) -> None:
    _initialized_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "contribution",
            "list",
            "PROP-999",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="proposal.contribution.list")
    assert error["code"] == "P2P_PROPOSAL_NOT_FOUND"
