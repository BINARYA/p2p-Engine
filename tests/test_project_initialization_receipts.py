from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml
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


def _init_json(root: Path, name: str, key: str):
    return runner.invoke(
        app,
        [
            "init",
            name,
            "--agent",
            "generic",
            "--owner",
            "owner",
            "--operation-key",
            key,
            "--format",
            "json",
            "--root",
            str(root),
        ],
    )


def test_init_json_writes_receipt_without_exposing_raw_operation_key(tmp_path: Path) -> None:
    operation_key = "wavekit:123e4567-e89b-12d3-a456-426614174000"

    result = _init_json(tmp_path, "Receipt Project", operation_key)

    assert result.exit_code == 0, result.output
    data = cli_data(result, operation="init")
    assert data["project_init"]["project"]["name"] == "Receipt Project"
    assert data["project_init"]["agent_selection"]["effective_profile"] == "generic"
    assert data["mutation"]["status"] == "applied"
    status = P2PWorkspace(tmp_path).mutation_status(idempotency_key=operation_key)
    assert status.state == "applied"
    assert status.operation == "init"
    receipt_paths = list((tmp_path / ".p2p" / ".internal" / "mutation-receipts").glob("*.yml"))
    assert len(receipt_paths) == 1
    assert operation_key not in receipt_paths[0].as_posix()
    assert operation_key not in receipt_paths[0].read_text(encoding="utf-8")


def test_init_json_all_agent_receipt_status_accepts_generated_adapter_files(
    tmp_path: Path,
) -> None:
    operation_key = "wavekit:123e4567-e89b-12d3-a456-426614174010"

    result = runner.invoke(
        app,
        [
            "init",
            "All Agent Receipt Project",
            "--agent",
            "all",
            "--owner",
            "owner",
            "--operation-key",
            operation_key,
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    data = cli_data(result, operation="init")
    assert ".cursor/rules/p2p.mdc" in data["project_init"]["created_paths"]
    assert ".github/copilot-instructions.md" in data["project_init"]["created_paths"]
    assert "CLAUDE.md" in data["project_init"]["created_paths"]
    assert "GEMINI.md" in data["project_init"]["created_paths"]

    status = runner.invoke(
        app,
        [
            "mutation",
            "status",
            "--operation-key",
            operation_key,
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
    )

    assert status.exit_code == 0, status.output
    status_data = cli_data(status, operation="mutation.status")
    assert status_data["state"] == "applied"
    assert status_data["operation"] == "init"
    assert status_data["postconditions_match"] is True


def test_init_json_exact_replay_returns_already_applied_without_side_effects(
    tmp_path: Path,
) -> None:
    operation_key = "wavekit:123e4567-e89b-12d3-a456-426614174001"
    first = _init_json(tmp_path, "Replay Project", operation_key)
    assert first.exit_code == 0, first.output
    before = _hash_tree(tmp_path)

    replay = _init_json(tmp_path, "Replay Project", operation_key)

    assert replay.exit_code == 0, replay.output
    data = cli_data(replay, operation="init")
    assert data["mutation"]["status"] == "already_applied"
    assert data["project_init"]["created_paths"] == cli_data(first)["project_init"]["created_paths"]
    assert _hash_tree(tmp_path) == before


def test_init_json_divergent_replay_conflicts_without_writes(tmp_path: Path) -> None:
    operation_key = "wavekit:123e4567-e89b-12d3-a456-426614174002"
    first = _init_json(tmp_path, "Conflict Project", operation_key)
    assert first.exit_code == 0, first.output
    before = _hash_tree(tmp_path)

    conflict = _init_json(tmp_path, "Different Project", operation_key)

    assert conflict.exit_code == 3
    error = cli_error(conflict, operation="init")
    assert error["code"] == "P2P_IDEMPOTENCY_CONFLICT"
    assert _hash_tree(tmp_path) == before


def test_init_json_can_attach_receipt_to_matching_existing_workspace(
    tmp_path: Path,
) -> None:
    P2PWorkspace(tmp_path).init_project("Existing Project", agent_profile="generic", owner="owner")
    before = _hash_tree(tmp_path)
    operation_key = "wavekit:123e4567-e89b-12d3-a456-426614174003"

    result = _init_json(tmp_path, "Existing Project", operation_key)

    assert result.exit_code == 0, result.output
    data = cli_data(result, operation="init")
    assert data["mutation"]["status"] == "applied"
    assert data["project_init"]["created_paths"] == []
    assert P2PWorkspace(tmp_path).mutation_status(idempotency_key=operation_key).state == "applied"
    assert _hash_tree(tmp_path) != before


def test_init_json_requires_operation_key(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "No Key", "--format", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="init")
    assert error["code"] == "P2P_IDEMPOTENCY_KEY_REQUIRED"


def test_init_json_rejects_unsupported_existing_schema(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Unsupported Project", agent_profile="generic", owner="owner")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    payload = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    payload["workspace_schema"]["current_version"] = 2
    schema_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    before = _hash_tree(tmp_path)

    result = _init_json(
        tmp_path,
        "Unsupported Project",
        "wavekit:123e4567-e89b-12d3-a456-426614174004",
    )

    assert result.exit_code == 3
    error = cli_error(result, operation="init")
    assert error["code"] == "P2P_WORKSPACE_UNSUPPORTED_SCHEMA"
    assert _hash_tree(tmp_path) == before


def test_init_json_rejects_pending_transaction_recovery(tmp_path: Path) -> None:
    P2PWorkspace(tmp_path).init_project("Locked Project", agent_profile="generic", owner="owner")
    lock_path = tmp_path / ".p2p" / ".internal" / "workspace-transactions" / "apply.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        yaml.safe_dump(
            {
                "transaction_id": "init-test",
                "pid": os.getpid(),
                "acquired_at": "2026-07-15T00:00:00Z",
                "owner": "test",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    before = _hash_tree(tmp_path)

    result = _init_json(
        tmp_path,
        "Locked Project",
        "wavekit:123e4567-e89b-12d3-a456-426614174005",
    )

    assert result.exit_code == 3
    error = cli_error(result, operation="init")
    assert error["code"] == "P2P_INIT_RECOVERY_REQUIRED"
    assert _hash_tree(tmp_path) == before
