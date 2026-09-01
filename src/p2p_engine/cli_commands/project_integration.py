from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_project_integration_commands(integration_app: typer.Typer) -> None:
    @integration_app.command("status")
    def integration_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            payload = workspace_for(root).project_integration_status()
        except ValueError as exc:
            fail(str(exc))
        _emit("integration.status", payload, output_format)

    @integration_app.command("install")
    def integration_install(
        profile: str = typer.Option("standalone", "--profile", help="Project access profile"),
        agent: str = typer.Option("generic", "--agent", help="Agent adapter id or all"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).install_project_integration(
                profile=profile,
                agent_target=agent,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit("integration.install", result.to_dict(), output_format)

    @integration_app.command("refresh")
    def integration_refresh(
        profile: str = typer.Option("standalone", "--profile", help="Project access profile"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).refresh_project_integration(profile=profile)
        except ValueError as exc:
            fail(str(exc))
        _emit("integration.refresh", result.to_dict(), output_format)

    @integration_app.command("profile")
    def integration_profile(
        profile: str = typer.Argument(..., help="standalone, linked-local, or remote-only"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).transition_project_integration(profile=profile)
        except ValueError as exc:
            fail(str(exc))
        _emit("integration.profile", result.to_dict(), output_format)

    @integration_app.command("remove")
    def integration_remove(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).remove_project_integration()
        except ValueError as exc:
            fail(str(exc))
        _emit("integration.remove", result.to_dict(), output_format)


def _emit(operation: str, payload: dict[str, object], output_format: str) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        print_json(success_envelope(operation, payload))
        return
    if normalized != "text":
        fail("Output format must be text or json.")
    console.print("Project integration")
    console.print(f"  operation: {payload.get('operation', 'status')}")
    console.print(f"  state: {payload.get('state', payload.get('status', 'unknown'))}")
    console.print(f"  profile: {payload.get('active_profile', payload.get('profile', '-'))}")
    changed = payload.get("changed_paths", [])
    if isinstance(changed, list) and changed:
        console.print("  changed:")
        for path in changed:
            console.print(f"    {path}")
    artifacts = payload.get("artifacts", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            console.print(
                f"  {artifact.get('path')}: {artifact.get('state')} "
                f"ownership={artifact.get('ownership')}"
            )
    if payload.get("message"):
        console.print(f"  message: {payload['message']}")

