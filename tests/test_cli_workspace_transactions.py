from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.mutation_preview import source_precondition
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_failure_result


runner = CliRunner()


def test_workspace_cli_exposes_current_schema_and_transaction_groups_only() -> None:
    result = runner.invoke(app, ["workspace", "--help"])

    assert result.exit_code == 0
    assert "schema" in result.output
    assert "transaction" in result.output
    assert "migrate" not in result.output


def test_workspace_schema_cli_rejects_missing_declaration_without_writes(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Unsupported CLI", owner="owner")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema_path.unlink()
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    result = runner.invoke(
        app,
        ["workspace", "schema", "status", "--format", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 3
    payload = cli_failure_result(result, operation="workspace.schema.status")
    assert payload["layout_status"] == "unsupported"
    assert payload["findings"][0]["code"] == "P2P_WORKSPACE_UNSUPPORTED_SCHEMA"
    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_workspace_transaction_cli_rolls_back_interrupted_current_write(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Transaction CLI", owner="Davide")
    target = tmp_path / ".p2p" / "project" / "questions.yml"
    before = target.read_bytes()

    def interrupt(stage: str, _target: str) -> None:
        if stage == "after_replace":
            target.write_bytes(b"external")
            raise RuntimeError("injected interruption")

    mutation = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=interrupt,
    ).apply(
        operation_id="cli-recovery",
        candidates={".p2p/project/questions.yml": b"candidate"},
        sources=(source_precondition(".p2p/project/questions.yml", before),),
        preview_token="cli-recovery-token",
        actor="Davide",
    )
    assert mutation.status == "recovery_required"

    status = runner.invoke(
        app,
        ["workspace", "transaction", "status", "--format", "json", "--root", str(tmp_path)],
    )
    assert status.exit_code == 1
    transaction_id = cli_failure_result(status)["transaction_id"]
    target.write_bytes(b"candidate")

    rollback = runner.invoke(
        app,
        [
            "workspace",
            "transaction",
            "rollback",
            transaction_id,
            "--actor",
            "Davide",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert rollback.exit_code == 0
    assert cli_data(rollback)["status"] == "rolled_back"
    assert target.read_bytes() == before
