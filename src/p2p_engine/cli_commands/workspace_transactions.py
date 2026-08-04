from __future__ import annotations

import json
from pathlib import Path

import typer

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_workspace_transaction_commands(transaction_app: typer.Typer) -> None:
    @transaction_app.command("status")
    def transaction_status(
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Inspect interrupted current-schema mutation transactions."""
        result = workspace_for(root).workspace_transaction_recovery_status()
        _emit(result.to_dict(), output_format)
        if result.required:
            raise typer.Exit(code=1)

    @transaction_app.command("rollback")
    def transaction_rollback(
        transaction_id: str = typer.Argument(..., help="Transaction identifier"),
        actor: str = typer.Option(..., "--actor", help="Authorized project owner"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm transaction rollback"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Rollback an interrupted atomic workspace mutation."""
        result = workspace_for(root).rollback_workspace_transaction(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )
        _emit(result.to_dict(), output_format)
        if result.status not in {"rolled_back", "no_op"}:
            raise typer.Exit(code=1)

    @transaction_app.command("resume")
    def transaction_resume(
        transaction_id: str = typer.Argument(..., help="Transaction identifier"),
        actor: str = typer.Option(..., "--actor", help="Authorized project owner"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm transaction resume"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Resume an interrupted atomic workspace mutation."""
        result = workspace_for(root).resume_workspace_transaction(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )
        _emit(result.to_dict(), output_format)
        if result.status != "applied":
            raise typer.Exit(code=1)


def _emit(payload: dict[str, object], output_format: str) -> None:
    if output_format == "json":
        console.out(json.dumps(payload, indent=2), highlight=False)
        return
    if output_format != "text":
        fail("Workspace transaction format must be text or json")
    for key, value in payload.items():
        if key not in {"lock", "restored_paths", "changed_paths", "available_actions"}:
            console.print(f"{key}: {value}")
    lock = payload.get("lock")
    if isinstance(lock, dict):
        console.print(f"lock_state: {lock.get('state')}")
        console.print(f"lock_path: {lock.get('path')}")
    for key in ("available_actions", "restored_paths", "changed_paths"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            console.print(f"{key}: {', '.join(str(item) for item in value)}")
