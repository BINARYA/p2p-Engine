from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.services.linked_replica import LinkedReplicaService


def register_linked_replica_commands(
    root_app: typer.Typer,
    wavekit_app: typer.Typer,
    sync_app: typer.Typer,
) -> None:
    replica_app = typer.Typer(help="Manage the identity of a linked local replica")
    drift_app = typer.Typer(help="Inspect and recover linked local replica drift")
    reconcile_app = typer.Typer(help="Restate recognized local drift as WaveKit commands")
    wavekit_sync_app = typer.Typer(help="Legacy alias for linked-replica synchronization")
    wavekit_app.add_typer(replica_app, name="replica")
    wavekit_app.add_typer(wavekit_sync_app, name="sync")
    root_app.add_typer(drift_app, name="drift")
    root_app.add_typer(reconcile_app, name="reconcile")

    @wavekit_app.command("clone")
    def clone(
        remote_project_id: str = typer.Argument(..., help="Opaque WaveKit project ID"),
        server: str = typer.Option(..., "--server", help="WaveKit server URL"),
        account_profile: str = typer.Option(..., "--account-profile"),
        operation_key: str = typer.Option(..., "--operation-key"),
        target: Path = typer.Option(Path.cwd(), "--target", help="New local workspace"),
        storage: str = typer.Option("filesystem", "--storage"),
        device_label: str = typer.Option("local-device", "--device-label"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        _require_filesystem(storage)
        try:
            result = LinkedReplicaService(root=target).clone(
                server_url=server,
                remote_project_id=remote_project_id,
                account_profile_ref=account_profile,
                operation_key=operation_key,
                confirm=confirm,
                device_label=device_label,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit("wavekit.clone", {"linked_replica": result.to_dict()}, output_format, result.message)

    @wavekit_app.command("attach")
    def attach(
        remote_project_id: str = typer.Argument(..., help="Opaque WaveKit project ID"),
        server: str = typer.Option(..., "--server", help="WaveKit server URL"),
        account_profile: str = typer.Option(..., "--account-profile"),
        operation_key: str = typer.Option(..., "--operation-key"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Existing workspace without .p2p"),
        storage: str = typer.Option("filesystem", "--storage"),
        device_label: str = typer.Option("local-device", "--device-label"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        _require_filesystem(storage)
        try:
            result = LinkedReplicaService(root=root).clone(
                server_url=server,
                remote_project_id=remote_project_id,
                account_profile_ref=account_profile,
                operation_key=operation_key,
                confirm=confirm,
                attach=True,
                device_label=device_label,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit("wavekit.attach", {"linked_replica": result.to_dict()}, output_format, result.message)

    @wavekit_app.command("status")
    def status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).linked_replica_status()
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.status",
            {"linked_replica_status": payload},
            output_format,
            f"Linked replica state: {payload['state']}",
        )

    @wavekit_sync_app.command("catch-up")
    @sync_app.command("catch-up")
    def catch_up(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).linked_replica_catch_up()
        except ValueError as exc:
            fail(str(exc))
        _emit("wavekit.sync.catch-up", {"linked_replica": result.to_dict()}, output_format, result.message)

    @wavekit_sync_app.command("recover")
    @sync_app.command("recover")
    def recover(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).linked_replica_recover()
        except ValueError as exc:
            fail(str(exc))
        _emit("wavekit.sync.recover", {"linked_replica": result.to_dict()}, output_format, result.message)

    @sync_app.command("status")
    def sync_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).linked_replica_status()
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "sync.status",
            {"linked_replica_status": payload},
            output_format,
            f"Linked replica state: {payload['state']}",
        )

    @root_app.command("watch")
    def watch(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        max_events: int = typer.Option(
            0,
            "--max-events",
            min=0,
            help="Stop after N events; zero keeps watching",
        ),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        normalized_format = output_format.strip().lower()
        if normalized_format == "json" and max_events == 0:
            fail(
                "P2P_REPLICATION_WATCH_BOUND_REQUIRED: JSON watch requires "
                "--max-events greater than zero"
            )
        if normalized_format not in {"text", "json"}:
            fail("P2P_CLI_INVALID_REQUEST: format must be text or json")
        service = LinkedReplicaService(root=root)
        if normalized_format == "text":
            observed = 0
            try:
                for event in service.iter_watch(max_events=max_events):
                    observed += 1
                    notification = event["notification"]
                    freshness = event["freshness"]
                    assert isinstance(notification, dict)
                    assert isinstance(freshness, dict)
                    console.print(
                        "Project revision "
                        f"{notification['project_revision']} is available; "
                        "the local replica is confirmed at revision "
                        f"{freshness['project_revision']}.",
                        markup=False,
                    )
            except (KeyboardInterrupt, EOFError):
                pass
            except ValueError as exc:
                fail(str(exc))
            console.print(f"Stopped after {observed} project notification(s).")
            return
        try:
            events = service.watch(max_events=max_events)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "watch",
            {"events": list(events), "event_count": len(events)},
            output_format,
            f"Observed {len(events)} project notification(s).",
        )

    @replica_app.command("move")
    def move(
        operation_key: str = typer.Option(..., "--operation-key"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).linked_replica_move(
                operation_key=operation_key, confirm=confirm
            )
        except ValueError as exc:
            fail(str(exc))
        _emit("wavekit.replica.move", {"linked_replica": result.to_dict()}, output_format, result.message)

    @replica_app.command("register-copy")
    def register_copy(
        operation_key: str = typer.Option(..., "--operation-key"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).linked_replica_register_copy(
                operation_key=operation_key, confirm=confirm
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.replica.register-copy",
            {"linked_replica": result.to_dict()},
            output_format,
            result.message,
        )

    @replica_app.command("read-only")
    def read_only(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).linked_replica_read_only()
        except ValueError as exc:
            fail(str(exc))
        _emit("wavekit.replica.read-only", {"linked_replica": result.to_dict()}, output_format, result.message)

    @drift_app.command("status")
    def drift_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).replica_drift_status()
        except ValueError as exc:
            fail(str(exc))
        payload = result.to_dict()
        _emit(
            "drift.status",
            {"replica_drift_status": payload},
            output_format,
            f"Replica integrity: {payload['status']} ({payload['classification'] or 'not-linked'}).",
        )

    @drift_app.command("verify")
    def drift_verify(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).replica_drift_verify()
        except ValueError as exc:
            fail(str(exc))
        payload = result.to_dict()
        _emit(
            "drift.verify",
            {"replica_drift_status": payload},
            output_format,
            "Local logical state matches its trusted evidence.",
        )

    @drift_app.command("diff")
    def drift_diff(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        limit: int = typer.Option(256, "--limit", min=1, max=256),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).replica_drift_diff(limit=limit)
        except ValueError as exc:
            fail(str(exc))
        payload = result.to_dict()
        _emit(
            "drift.diff",
            {"replica_semantic_diff": payload},
            output_format,
            f"Found {payload['entry_count']} bounded logical difference(s).",
        )

    @drift_app.command("backup")
    def drift_backup(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).replica_drift_backup()
        except ValueError as exc:
            fail(str(exc))
        payload = result.to_dict()
        _emit(
            "drift.backup",
            {"forensic_backup": payload},
            output_format,
            f"Verified forensic backup created: {payload['backup_ref']}.",
        )

    @drift_app.command("report")
    def drift_report(
        include_diff: bool = typer.Option(True, "--include-diff/--no-include-diff"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).replica_drift_report(
                include_diff=include_diff
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "drift.report",
            {"replica_health": dict(payload)},
            output_format,
            "Sanitized replica health evidence was reported to WaveKit.",
        )

    @drift_app.command("discard")
    def drift_discard(
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).replica_drift_discard(confirm=confirm)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "drift.discard",
            {"replica_drift_rebuild": payload},
            output_format,
            "Local drift was preserved and replaced from WaveKit authority.",
        )

    @reconcile_app.command("preview")
    def reconcile_preview(
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).replica_reconciliation_preview()
        except ValueError as exc:
            fail(str(exc))
        payload = result.to_dict()
        _emit(
            "reconcile.preview",
            {"reconciliation_plan": payload},
            output_format,
            f"Reconciliation plan {payload['plan_digest']} is {'complete' if payload['complete'] else 'blocked'}.",
        )

    @reconcile_app.command("apply")
    def reconcile_apply(
        plan_digest: str = typer.Option(..., "--plan-digest"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Linked project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).replica_reconciliation_apply(
                plan_digest=plan_digest,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "reconcile.apply",
            {"reconciliation_result": payload},
            output_format,
            "Recognized intent was applied through normal WaveKit commands.",
        )


def _require_filesystem(storage: str) -> None:
    if storage.strip().lower() != "filesystem":
        fail("P2P_STORAGE_ADAPTER_UNAVAILABLE: this release selected the filesystem backend")


def _emit(operation: str, payload: object, output_format: str, text: str) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        print_json(success_envelope(operation, payload))
        return
    if normalized != "text":
        fail("P2P_CLI_INVALID_REQUEST: format must be text or json")
    console.print(text)
