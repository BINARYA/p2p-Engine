from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_spec_commands(spec_app: typer.Typer) -> None:
    @spec_app.command("refresh")
    def spec_refresh(
        change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a deterministic P2P-native software spec from a Change Set."""
        try:
            status = workspace_for(root).refresh_software_spec(change)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Software spec refreshed.[/green]")
        console.print(f"  change: {status.change_id}")
        console.print(f"  status: {status.status}")
        console.print(f"  path: {status.path}")

    @spec_app.command("status")
    def spec_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List generated software specs."""
        specs = workspace_for(root).software_spec_statuses()
        console.print("Software Specs")
        if not specs:
            console.print("  none")
            return
        for spec in specs:
            console.print(f"  {spec.change_id}  {spec.status}  {spec.title}")

    @spec_app.command("show")
    def spec_show(
        change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a generated software spec index."""
        try:
            content = workspace_for(root).show_software_spec(change_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(content)

    @spec_app.command("prompt")
    def spec_prompt(
        change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a prompt for AI/human software spec refinement."""
        try:
            prompt = workspace_for(root).create_software_spec_prompt(change)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Software spec prompt created.[/green]")
        console.print(f"  change: {prompt.change_id}")
        console.print(f"  prompt: {prompt.prompt_path}")

    @spec_app.command("import")
    def spec_import(
        change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
        source: Path = typer.Argument(..., help="Directory containing refined software spec artifacts"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import a validated refined software spec."""
        try:
            imported = workspace_for(root).import_software_spec(change_id, source)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Software spec imported.[/green]")
        for path in imported:
            console.print(f"  updated {path}")

    @spec_app.command("export")
    def spec_export(
        change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
        target: str = typer.Option(..., "--target", help="Export target: generic, openspec, or speckit"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Export P2P project definition outputs for an agent/downstream target."""
        try:
            status = workspace_for(root).export_software_spec(change, target)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Software spec exported.[/green]")
        console.print(f"  change: {status.change_id}")
        console.print(f"  target: {status.target}")
        console.print(f"  status: {status.status}")
        console.print(f"  path: {status.path}")

    @spec_app.command("export-status")
    def spec_export_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List generated software spec exports."""
        exports = workspace_for(root).software_spec_export_statuses()
        console.print("Software Spec Exports")
        if not exports:
            console.print("  none")
            return
        for export in exports:
            console.print(f"  {export.change_id}  {export.target}  {export.status}  {export.title}")

    @spec_app.command("export-show")
    def spec_export_show(
        change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
        target: str = typer.Option(..., "--target", help="Export target: generic, openspec, or speckit"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show the primary software spec export document."""
        try:
            content = workspace_for(root).show_software_spec_export(change_id, target)
        except ValueError as exc:
            fail(str(exc))
        console.print(content)

    @spec_app.command("export-validate")
    def spec_export_validate(
        change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
        target: str = typer.Option(..., "--target", help="Export target: generic, openspec, or speckit"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Validate an existing software spec export."""
        try:
            validation = workspace_for(root).validate_software_spec_export(change_id, target)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Software spec export valid.[/green]")
        console.print(f"  change: {validation.change_id}")
        console.print(f"  target: {validation.target}")
        console.print(f"  path: {validation.path}")
        console.print("  checked:")
        for path in validation.checked:
            console.print(f"    ✓ {path}")
