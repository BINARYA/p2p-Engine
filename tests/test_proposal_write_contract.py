from __future__ import annotations

import hashlib
from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
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


def _initialized_workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Proposal Write Contract", owner="owner", vertical_id="base_project")
    return workspace


def _create_json(root: Path, key: str, title: str = "JSON proposal"):
    return runner.invoke(
        app,
        [
            "proposal",
            "create",
            title,
            "--problem",
            "WaveKit needs receipt-backed proposal creation.",
            "--context",
            "The worker can lose a response after the CLI commits.",
            "--goal",
            "Return a durable JSON mutation result.",
            "--proposal",
            "Create the proposal atomically with a receipt.",
            "--acceptance",
            "Exact retry returns already_applied.",
            "--operation-key",
            key,
            "--actor",
            "wavekit",
            "--format",
            "json",
            "--root",
            str(root),
        ],
    )


def test_proposal_create_json_writes_receipt_and_replays_without_writes(tmp_path: Path) -> None:
    _initialized_workspace(tmp_path)
    key = "wavekit:123e4567-e89b-12d3-a456-426614174100"

    result = _create_json(tmp_path, key)

    assert result.exit_code == 0, result.output
    data = cli_data(result, operation="proposal.create")
    created = data["proposal_create"]
    mutation = data["mutation"]
    proposal = created["proposal"]
    assert mutation["status"] == "applied"
    assert mutation["operation_id"] == "proposal.create"
    assert proposal["proposal_id"] == "PROP-001"
    assert proposal["path"].startswith(".p2p/proposals/PROP-001-")
    assert any(path.endswith("/artifact-state.yml") for path in created["created_paths"])
    status = P2PWorkspace(tmp_path).mutation_status(idempotency_key=key)
    assert status.state == "applied"
    assert status.operation == "proposal_create"
    assert status.result["proposal"]["proposal_id"] == "PROP-001"
    before = _hash_tree(tmp_path)

    replay = _create_json(tmp_path, key)

    assert replay.exit_code == 0, replay.output
    replay_data = cli_data(replay, operation="proposal.create")
    assert replay_data["mutation"]["status"] == "already_applied"
    assert replay_data["proposal_create"]["proposal"] == proposal
    assert _hash_tree(tmp_path) == before


def test_proposal_create_json_divergent_replay_conflicts_without_writes(tmp_path: Path) -> None:
    _initialized_workspace(tmp_path)
    key = "wavekit:123e4567-e89b-12d3-a456-426614174101"
    first = _create_json(tmp_path, key)
    assert first.exit_code == 0, first.output
    before = _hash_tree(tmp_path)

    conflict = _create_json(tmp_path, key, title="Different JSON proposal")

    assert conflict.exit_code == 3
    error = cli_error(conflict, operation="proposal.create")
    assert error["code"] == "P2P_IDEMPOTENCY_CONFLICT"
    assert _hash_tree(tmp_path) == before


def test_proposal_create_json_requires_operation_key(tmp_path: Path) -> None:
    _initialized_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "create",
            "No operation key",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="proposal.create")
    assert error["code"] == "P2P_IDEMPOTENCY_KEY_REQUIRED"


def test_proposal_update_json_writes_receipt_and_replays_without_writes(tmp_path: Path) -> None:
    workspace = _initialized_workspace(tmp_path)
    proposal = workspace.create_proposal_with_details(
        title="Update target",
        problem="The original problem is thin.",
        proposal="The original proposal is thin.",
    )
    key = "wavekit:123e4567-e89b-12d3-a456-426614174102"

    result = runner.invoke(
        app,
        [
            "proposal",
            "update",
            proposal.proposal_id,
            "--problem",
            "The updated problem is explicit.",
            "--goal",
            "Expose update receipts.",
            "--operation-key",
            key,
            "--actor",
            "wavekit",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    data = cli_data(result, operation="proposal.update")
    assert data["mutation"]["status"] == "applied"
    assert data["proposal_update"]["proposal_id"] == proposal.proposal_id
    assert data["proposal_update"]["updated_sections"] == ["problem", "goals"]
    content = (tmp_path / proposal.path / "proposal.md").read_text(encoding="utf-8")
    assert "The updated problem is explicit." in content
    assert "- Expose update receipts." in content
    status = P2PWorkspace(tmp_path).mutation_status(idempotency_key=key)
    assert status.state == "applied"
    assert status.operation == "proposal_update"
    before = _hash_tree(tmp_path)

    replay = runner.invoke(
        app,
        [
            "proposal",
            "update",
            proposal.proposal_id,
            "--problem",
            "The updated problem is explicit.",
            "--goal",
            "Expose update receipts.",
            "--operation-key",
            key,
            "--actor",
            "wavekit",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert replay.exit_code == 0, replay.output
    replay_data = cli_data(replay, operation="proposal.update")
    assert replay_data["mutation"]["status"] == "already_applied"
    assert _hash_tree(tmp_path) == before


def test_proposal_update_json_rejects_missing_proposal_without_writes(tmp_path: Path) -> None:
    _initialized_workspace(tmp_path)
    before = _hash_tree(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "update",
            "PROP-999",
            "--problem",
            "Missing target.",
            "--operation-key",
            "wavekit:123e4567-e89b-12d3-a456-426614174103",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="proposal.update")
    assert error["code"] == "P2P_PROPOSAL_NOT_FOUND"
    assert _hash_tree(tmp_path) == before


def test_proposal_update_json_rejects_empty_update_without_writes(tmp_path: Path) -> None:
    workspace = _initialized_workspace(tmp_path)
    proposal = workspace.create_proposal_with_details(title="Empty update target")
    before = _hash_tree(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "update",
            proposal.proposal_id,
            "--operation-key",
            "wavekit:123e4567-e89b-12d3-a456-426614174104",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="proposal.update")
    assert error["code"] == "P2P_PROPOSAL_EMPTY_UPDATE"
    assert _hash_tree(tmp_path) == before
