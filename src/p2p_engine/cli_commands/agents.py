from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_agent_commands(agent_app: typer.Typer, agent_instructions_app: typer.Typer) -> None:
    @agent_instructions_app.command("refresh")
    def agent_instructions_refresh(
        profile: str = typer.Option(
            "generic",
            "--profile",
            "--agent",
            help="Agent profile to add or refresh: generic, codex, claude, or all",
        ),
        repository: str | None = typer.Option(
            None,
            "--repository",
            help="Repository mode override: local or cloud",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Refresh agent-safe project instructions without removing other profiles."""
        try:
            result = workspace_for(root).refresh_agent_instructions(
                profile=profile,
                repository_mode=repository,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Agent instructions refreshed.[/green]")
        console.print(f"  profile: {result.profile}")
        console.print(f"  policy: {result.policy_path}")
        if result.created:
            console.print("  created:")
            for path in result.created:
                console.print(f"    {path}")
        if result.updated:
            console.print("  updated:")
            for path in result.updated:
                console.print(f"    {path}")
        if not result.created and not result.updated:
            console.print("  no changes")

    @agent_app.command("list")
    def agent_list(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List supported and installed agent integrations."""
        result = workspace_for(root).agent_integrations_list()
        console.print("Agent integrations")
        console.print(f"  registry: {result['registry_path']}")
        console.print(f"  baseline: {result['baseline_profile']}")
        for adapter in result["adapters"]:
            console.print(
                f"  {adapter['adapter']}: installed={str(adapter['installed']).lower()} "
                f"drift={adapter['drift']}"
            )

    @agent_app.command("show")
    def agent_show(
        adapter: str = typer.Argument(..., help="Agent adapter id"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show an agent integration and its managed files."""
        try:
            result = workspace_for(root).agent_integration_show(adapter)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"Agent integration: {result['adapter']}")
        console.print(f"  installed: {str(result['installed']).lower()}")
        console.print(f"  drift: {result['drift']}")
        console.print("  files:")
        for record in result.get("files", []):
            console.print(
                f"    {record['path']} shared={str(record.get('shared')).lower()} "
                f"owner={record.get('owner')} drift={record.get('drift')}"
            )

    @agent_app.command("install")
    def agent_install(
        target: str = typer.Argument(..., help="Agent adapter id or all"),
        force: bool = typer.Option(False, "--force", help="Overwrite drifted or unmanaged files"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Install agent integration files and update the registry."""
        try:
            result = workspace_for(root).install_agent_integrations(target, force=force)
        except ValueError as exc:
            fail(str(exc))
        _print_agent_integration_result("Agent integration installed", result)

    @agent_app.command("update")
    def agent_update(
        target: str = typer.Argument(..., help="Agent adapter id or all"),
        force: bool = typer.Option(False, "--force", help="Overwrite drifted or unmanaged files"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Update generated agent integration files when safe."""
        try:
            result = workspace_for(root).install_agent_integrations(target, force=force)
        except ValueError as exc:
            fail(str(exc))
        _print_agent_integration_result("Agent integration updated", result)

    @agent_app.command("uninstall")
    def agent_uninstall(
        adapter: str = typer.Argument(..., help="Agent adapter id"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Uninstall a safe, managed, non-shared agent integration."""
        try:
            result = workspace_for(root).uninstall_agent_integration(adapter)
        except ValueError as exc:
            fail(str(exc))
        _print_agent_integration_result("Agent integration uninstalled", result)


def _print_agent_integration_result(title: str, result: object) -> None:
    console.print(f"[green]{title}.[/green]")
    console.print(f"  target: {result.target}")
    console.print(f"  registry: {result.registry_path}")
    for label in ("created", "updated", "removed"):
        items = getattr(result, label)
        if items:
            console.print(f"  {label}:")
            for path in items:
                console.print(f"    {path}")
    if result.skipped:
        console.print("  skipped:")
        for item in result.skipped:
            console.print(f"    {item['path']}: {item['reason']}")
