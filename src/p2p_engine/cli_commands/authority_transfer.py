from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_authority_transfer_commands(
    auth_app: typer.Typer,
    project_app: typer.Typer,
) -> None:
    transfer_app = typer.Typer(
        help="Preview, apply and recover an owner-controlled authority handoff to WaveKit"
    )
    project_app.add_typer(transfer_app, name="transfer")

    @auth_app.command("login")
    def auth_login(
        server: str = typer.Argument(..., help="WaveKit server URL"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            workspace = workspace_for(root)
            capabilities, authorization = workspace.wavekit_auth_start(server)
            instruction = (
                f"Open {authorization.verification_uri} and enter code "
                f"{authorization.user_code}"
            )
            if output_format == "json":
                typer.echo(instruction, err=True)
            else:
                console.print(instruction)
            credential = workspace.wavekit_auth_complete(capabilities, authorization)
        except ValueError as exc:
            fail(str(exc))
        payload = {
            "contract": "p2p-wavekit-auth-login/v1",
            "server_url": capabilities.server_url,
            "server_instance_id": capabilities.server_instance_id.value,
            "authorization": authorization.public_dict(),
            "credential": credential.public_dict(),
        }
        _emit("auth.login", payload, output_format, "WaveKit login completed.")

    @auth_app.command("status")
    def auth_status(
        server: str = typer.Argument(..., help="WaveKit server URL"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).wavekit_auth_status(server)
        except ValueError as exc:
            fail(str(exc))
        authenticated = bool(payload["credential"]["authenticated"])
        _emit(
            "auth.status",
            payload,
            output_format,
            f"WaveKit authentication: {'active' if authenticated else 'absent'}.",
        )

    @auth_app.command("logout")
    def auth_logout(
        server: str = typer.Argument(..., help="WaveKit server URL"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).wavekit_auth_logout(server)
        except ValueError as exc:
            fail(str(exc))
        _emit("auth.logout", payload, output_format, "WaveKit credential removed.")

    @transfer_app.command("preview")
    def transfer_preview(
        server: str = typer.Option(..., "--server", help="WaveKit server URL"),
        owner_profile: str = typer.Option(..., "--owner-profile", help="WaveKit owner profile"),
        operation_key: str = typer.Option(..., "--operation-key"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            preview = workspace_for(root).preview_authority_transfer(
                server_url=server,
                owner_profile_ref=owner_profile,
                operation_key=operation_key,
            )
        except ValueError as exc:
            fail(str(exc))
        payload = {"authority_transfer_preview": preview.to_dict()}
        text = "\n".join(
            [
                "Authority transfer preview",
                f"  eligible: {'yes' if preview.eligible else 'no'}",
                f"  project UUID: {preview.project_uuid.value}",
                f"  destination: {preview.server_url}",
                f"  entities: {preview.entity_count}",
                f"  managed blobs: {preview.blob_count} ({preview.blob_bytes} bytes)",
                "  authority after apply: WaveKit",
                f"  preview token: {preview.preview_token}",
            ]
        )
        _emit("project.transfer.preview", payload, output_format, text)

    @transfer_app.command("apply")
    def transfer_apply(
        server: str = typer.Option(..., "--server", help="WaveKit server URL"),
        owner_profile: str = typer.Option(..., "--owner-profile", help="WaveKit owner profile"),
        operation_key: str = typer.Option(..., "--operation-key"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).apply_authority_transfer(
                server_url=server,
                owner_profile_ref=owner_profile,
                operation_key=operation_key,
                preview_token=preview_token,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.transfer.apply",
            {"authority_transfer": result.to_dict()},
            output_format,
            result.message,
        )

    @transfer_app.command("status")
    def transfer_status(
        server: str = typer.Option("", "--server", help="Optionally query WaveKit"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).authority_transfer_status(server_url=server)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.transfer.status",
            {"authority_transfer_status": payload},
            output_format,
            f"Authority transfer state: {payload['state']}",
        )

    @transfer_app.command("recover")
    def transfer_recover(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).recover_authority_transfer()
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.transfer.recover",
            {"authority_transfer": result.to_dict()},
            output_format,
            result.message,
        )


def _emit(operation: str, payload: object, output_format: str, text: str) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        print_json(success_envelope(operation, payload))
        return
    if normalized != "text":
        fail("P2P_CLI_INVALID_REQUEST: format must be text or json")
    console.print(text)
