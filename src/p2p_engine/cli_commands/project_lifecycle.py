from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.project_lifecycle import LifecycleAction


def register_project_lifecycle_commands(wavekit_app: typer.Typer) -> None:
    lifecycle_app = typer.Typer(
        help="Preview, apply, inspect, and recover governed project lifecycle operations"
    )
    wavekit_app.add_typer(lifecycle_app, name="lifecycle")

    @lifecycle_app.command("status")
    def lifecycle_status(
        root: Path = typer.Option(Path.cwd(), "--root"),
        offline: bool = typer.Option(False, "--offline", help="Inspect only local evidence"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        try:
            payload = workspace_for(root).project_lifecycle_status(online=not offline)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.lifecycle.status",
            {"project_lifecycle": payload},
            output_format,
            _status_text(payload),
        )

    @lifecycle_app.command("preview")
    def lifecycle_preview(
        action: str = typer.Argument(..., help="Lifecycle action"),
        operation_id: str = typer.Option(..., "--operation-id"),
        target: Path | None = typer.Option(None, "--target"),
        lineage_mode: str = typer.Option("", "--lineage-mode"),
        keep_local: bool = typer.Option(False, "--keep-local"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        try:
            preview = workspace_for(root).preview_project_lifecycle(
                action=action,
                operation_id=operation_id,
                target=target,
                lineage_mode=lineage_mode,
                keep_local=keep_local,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.lifecycle.preview",
            {"project_lifecycle_preview": preview.to_dict()},
            output_format,
            f"Lifecycle {preview.action.value} preview: "
            f"{'eligible' if preview.eligible else 'blocked'}.",
        )

    @lifecycle_app.command("apply")
    def lifecycle_apply(
        action: str = typer.Argument(
            ..., help="suspend, resume, archive, restore, or delete-remote"
        ),
        operation_id: str = typer.Option(..., "--operation-id"),
        preview_token: str = typer.Option(..., "--preview-token"),
        keep_local: bool = typer.Option(False, "--keep-local"),
        detached_root: Path | None = typer.Option(None, "--detached-root"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        _remote_apply(
            action=action,
            operation_id=operation_id,
            preview_token=preview_token,
            keep_local=keep_local,
            detached_root=detached_root,
            confirm=confirm,
            root=root,
            output_format=output_format,
            operation="wavekit.lifecycle.apply",
        )

    @lifecycle_app.command("recover")
    def lifecycle_recover(
        operation_id: str = typer.Argument(...),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        try:
            payload = workspace_for(root).recover_project_lifecycle(operation_id=operation_id)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.lifecycle.recover",
            {"project_lifecycle_recovery": payload},
            output_format,
            f"Lifecycle operation {operation_id}: {payload['status']}.",
        )

    for action in (
        LifecycleAction.suspend,
        LifecycleAction.resume,
        LifecycleAction.archive,
        LifecycleAction.restore,
    ):
        _register_remote_shortcut(wavekit_app, action)

    @wavekit_app.command("delete-remote")
    def delete_remote(
        operation_id: str = typer.Option(..., "--operation-id"),
        preview_token: str = typer.Option(..., "--preview-token"),
        keep_local: bool = typer.Option(False, "--keep-local"),
        detached_root: Path | None = typer.Option(None, "--detached-root"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        _remote_apply(
            action=LifecycleAction.delete_remote.value,
            operation_id=operation_id,
            preview_token=preview_token,
            keep_local=keep_local,
            detached_root=detached_root,
            confirm=confirm,
            root=root,
            output_format=output_format,
            operation="wavekit.delete-remote",
        )

    @wavekit_app.command("detach")
    def detach(
        operation_id: str = typer.Option(..., "--operation-id"),
        preview_token: str = typer.Option(..., "--preview-token"),
        target: Path = typer.Option(..., "--target"),
        local_owner: str = typer.Option(..., "--local-owner"),
        preserve_origin: bool = typer.Option(False, "--preserve-origin"),
        private_origin: bool = typer.Option(False, "--private-origin"),
        drop_origin: bool = typer.Option(False, "--drop-origin"),
        as_independent: bool = typer.Option(False, "--as-independent"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        choices = [
            name
            for name, selected in (
                ("preserve-origin", preserve_origin),
                ("private-origin", private_origin),
                ("drop-origin", drop_origin),
            )
            if selected
        ]
        if not as_independent:
            fail("P2P_PROJECT_LIFECYCLE_INVALID: detach requires --as-independent")
        if len(choices) != 1:
            fail(
                "P2P_PROJECT_LIFECYCLE_INVALID: select exactly one of "
                "--preserve-origin, --private-origin, or --drop-origin"
            )
        try:
            receipt = workspace_for(root).detach_linked_project(
                operation_id=operation_id,
                preview_token=preview_token,
                target=target,
                local_owner=local_owner,
                lineage_mode=choices[0],
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.detach",
            {"detach_receipt": receipt.to_dict()},
            output_format,
            f"Detached independent project {receipt.new_project_uuid.value}.",
        )

    @wavekit_app.command("create-from-local")
    def create_from_local(
        server: str = typer.Option(..., "--server"),
        owner_profile_ref: str = typer.Option(..., "--owner-profile-ref"),
        operation_key: str = typer.Option(..., "--operation-key"),
        preview_token: str = typer.Option("", "--preview-token"),
        lineage_visibility: str = typer.Option(..., "--lineage-visibility"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        try:
            workspace = workspace_for(root)
            identity = workspace.project_identity()
            if lineage_visibility not in {"preserved", "private", "dropped"}:
                raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: lineage visibility is unsupported")
            if identity.lineage:
                actual = identity.lineage[-1].visibility.value
                if lineage_visibility != actual:
                    raise ValueError(
                        "P2P_PROJECT_LIFECYCLE_LINEAGE_MISMATCH: selected visibility differs from the detached identity"
                    )
            elif lineage_visibility != "dropped":
                raise ValueError(
                    "P2P_PROJECT_LIFECYCLE_LINEAGE_MISMATCH: project has no retained lineage"
                )
            if preview_token:
                result = workspace.apply_authority_transfer(
                    server_url=server,
                    owner_profile_ref=owner_profile_ref,
                    operation_key=operation_key,
                    preview_token=preview_token,
                    confirm=confirm,
                )
                data = {"authority_transfer": result.to_dict()}
                text = result.message
            else:
                result = workspace.preview_authority_transfer(
                    server_url=server,
                    owner_profile_ref=owner_profile_ref,
                    operation_key=operation_key,
                )
                data = {"authority_transfer_preview": result.to_dict()}
                text = "Create-from-local authority transfer preview prepared."
        except ValueError as exc:
            fail(str(exc))
        _emit("wavekit.create-from-local", data, output_format, text)

    @wavekit_app.command("publish-copy")
    def publish_copy(
        operation_id: str = typer.Option(..., "--operation-id"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        try:
            publication = workspace_for(root).publish_linked_project_copy(
                operation_id=operation_id,
                preview_token=preview_token,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.publish-copy",
            {"project_publication": publication.to_dict()},
            output_format,
            f"Published immutable copy {publication.publication_id} v{publication.version}.",
        )

    @wavekit_app.command("remove-local-replica")
    def remove_local_replica(
        operation_id: str = typer.Option(..., "--operation-id"),
        preview_token: str = typer.Option(..., "--preview-token"),
        disposition: str = typer.Option(..., "--disposition", help="archive or remove"),
        integration: str = typer.Option(
            ...,
            "--integration",
            help="remove or remote-only",
        ),
        archive_to: Path | None = typer.Option(None, "--archive-to"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        try:
            result = workspace_for(root).remove_local_linked_replica(
                operation_id=operation_id,
                preview_token=preview_token,
                disposition=disposition,
                integration=integration,
                archive_to=archive_to,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "wavekit.remove-local-replica",
            {"local_replica_removal": result},
            output_format,
            "Local replica removed; the WaveKit project was not deleted.",
        )


def _register_remote_shortcut(wavekit_app: typer.Typer, action: LifecycleAction) -> None:
    def command(
        operation_id: str = typer.Option(..., "--operation-id"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format"),
    ) -> None:
        _remote_apply(
            action=action.value,
            operation_id=operation_id,
            preview_token=preview_token,
            keep_local=False,
            detached_root=None,
            confirm=confirm,
            root=root,
            output_format=output_format,
            operation=f"wavekit.{action.value}",
        )

    command.__name__ = action.value.replace("-", "_")
    wavekit_app.command(action.value)(command)


def _remote_apply(
    *,
    action: str,
    operation_id: str,
    preview_token: str,
    keep_local: bool,
    detached_root: Path | None,
    confirm: bool,
    root: Path,
    output_format: str,
    operation: str,
) -> None:
    try:
        receipt = workspace_for(root).apply_project_lifecycle(
            action=action,
            operation_id=operation_id,
            preview_token=preview_token,
            keep_local=keep_local,
            detached_root=detached_root,
            confirm=confirm,
        )
    except ValueError as exc:
        fail(str(exc))
    _emit(
        operation,
        {"project_lifecycle_receipt": receipt.to_dict()},
        output_format,
        receipt.message or f"Lifecycle {action} completed.",
    )


def _status_text(payload: dict[str, object]) -> str:
    remote = payload.get("remote")
    if isinstance(remote, dict):
        return f"Remote project lifecycle state: {remote.get('state', 'unknown')}."
    diagnostic = payload.get("diagnostic")
    return f"Remote lifecycle unavailable: {diagnostic or 'no linked remote'}."


def _emit(operation: str, payload: object, output_format: str, text: str) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        print_json(success_envelope(operation, payload))
        return
    if normalized != "text":
        fail("P2P_CLI_INVALID_REQUEST: format must be text or json")
    console.print(text)
