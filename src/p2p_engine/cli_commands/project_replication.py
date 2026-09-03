from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.services.project_replication import FilesystemProjectReplicationStore


def register_project_replication_commands(project_app: typer.Typer) -> None:
    replication_app = typer.Typer(
        help="WaveKit worker-only durable project replication contracts"
    )
    project_app.add_typer(replication_app, name="replication")

    @replication_app.command("initialize")
    def initialize(
        authority_epoch: int = typer.Option(..., "--authority-epoch", min=1),
        project_revision: int = typer.Option(..., "--project-revision", min=0),
        retention_batches: int = typer.Option(2048, "--retention-batches", min=1),
        root: Path = typer.Option(Path.cwd(), "--root"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        if not confirm:
            fail("P2P_CONFIRMATION_REQUIRED: replication initialization requires --confirm")
        try:
            state = FilesystemProjectReplicationStore(root).initialize(
                authority_epoch=authority_epoch,
                project_revision=project_revision,
                retention_batches=retention_batches,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.replication.initialize",
            {"replication_state": state.to_dict()},
            output_format,
            f"Durable project replication initialized at revision {state.current_revision}.",
        )

    @replication_app.command("status")
    def status(
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            state = FilesystemProjectReplicationStore(root).state()
        except ValueError as exc:
            fail(str(exc))
        payload = state.to_dict() if state is not None else None
        _emit(
            "project.replication.status",
            {"replication_state": payload},
            output_format,
            (
                "Durable project replication is not initialized."
                if state is None
                else f"Durable project replication head is {state.current_revision}."
            ),
        )

    @replication_app.command("operation-status")
    def operation_status(
        operation_id: str = typer.Argument(...),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            receipt = FilesystemProjectReplicationStore(root).receipt(operation_id)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.replication.operation-status",
            {"operation_receipt": receipt.to_dict() if receipt is not None else None},
            output_format,
            "Operation receipt found." if receipt is not None else "Operation receipt not found.",
        )

    @replication_app.command("feed")
    def feed(
        after_revision: int = typer.Option(..., "--after-revision", min=0),
        replica_id: str = typer.Option(..., "--replica-id"),
        limit: int = typer.Option(64, "--limit", min=1, max=128),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            page = FilesystemProjectReplicationStore(root).feed(
                after_revision=after_revision,
                replica_id=replica_id,
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.replication.feed",
            {"project_change_feed": page.to_dict()},
            output_format,
            f"Feed {page.status}: revision {page.to_revision} of {page.current_revision}.",
        )

    @replication_app.command("compact")
    def compact(
        retain_after_revision: int = typer.Option(..., "--retain-after-revision", min=0),
        root: Path = typer.Option(Path.cwd(), "--root"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        if not confirm:
            fail("P2P_CONFIRMATION_REQUIRED: feed compaction requires --confirm")
        try:
            state = FilesystemProjectReplicationStore(root).compact(
                retain_after_revision=retain_after_revision
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.replication.compact",
            {"replication_state": state.to_dict()},
            output_format,
            f"Feed retention floor is now revision {state.oldest_available_revision}.",
        )


def _emit(operation: str, payload: object, output_format: str, message: str) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        print_json(success_envelope(operation, payload))
        return
    if normalized != "text":
        fail("P2P_CLI_INVALID_REQUEST: format must be text or json")
    console.print(message)
