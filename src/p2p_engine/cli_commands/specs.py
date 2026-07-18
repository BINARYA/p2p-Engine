from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_spec_commands(spec_app: typer.Typer) -> None:
    @spec_app.command("lifecycle")
    def spec_lifecycle(
        intent: str = typer.Option("implementation_spec", "--intent", help="Lifecycle intent"),
        change: str | None = typer.Option(None, "--change", help="Change Set ID, e.g. CHANGE-001"),
        target: str | None = typer.Option(None, "--target", help="Export target when intent is downstream_export"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show governed software-spec lifecycle guidance without writing state."""
        try:
            view = workspace_for(root).software_spec_lifecycle(intent, change_id=change, target=target)
        except ValueError as exc:
            fail(str(exc))
        console.print("Software spec lifecycle")
        _print_lifecycle(view)

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
        if status.lifecycle is not None:
            _print_lifecycle(status.lifecycle, indent="  ")

    @spec_app.command("status")
    def spec_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List generated software specs."""
        specs = workspace_for(root).software_spec_statuses()
        console.print("Software Specs")
        if not specs:
            console.print("  none")
            return
        for spec in specs:
            console.print(
                f"  {spec.change_id}  {spec.status}  {spec.title}"
                f"  freshness={spec.freshness}"
            )

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
        """Export a software-spec handoff bundle for a downstream target."""
        try:
            status = workspace_for(root).export_software_spec(change, target)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Software spec exported.[/green]")
        console.print(f"  change: {status.change_id}")
        console.print(f"  target: {status.target}")
        console.print(f"  status: {status.status}")
        console.print(f"  path: {status.path}")
        if status.lifecycle is not None:
            _print_lifecycle(status.lifecycle, indent="  ")

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


def _print_lifecycle(view: object, *, indent: str = "  ") -> None:
    console.print(f"{indent}intent: {getattr(view, 'intent')}")
    console.print(f"{indent}route: {getattr(view, 'route')}")
    console.print(f"{indent}write_class: {getattr(view, 'write_class')}")
    console.print(f"{indent}canonical_status: {getattr(view, 'canonical_status')}")
    console.print(f"{indent}writes_state: {str(getattr(view, 'writes_state')).lower()}")
    if getattr(view, "change_id", ""):
        console.print(f"{indent}change: {getattr(view, 'change_id')}")
    if getattr(view, "target", ""):
        console.print(f"{indent}target: {getattr(view, 'target')}")
    _print_diagnostics("blockers", getattr(view, "blockers", []), indent=indent)
    _print_diagnostics("advisories", getattr(view, "advisories", []), indent=indent)
    commands = getattr(view, "suggested_commands", [])
    if commands:
        console.print(f"{indent}suggested_commands:")
        for command in commands:
            console.print(f"{indent}  - {command}")


def _print_diagnostics(label: str, diagnostics: list[object], *, indent: str) -> None:
    if not diagnostics:
        console.print(f"{indent}{label}: none")
        return
    console.print(f"{indent}{label}:")
    for diagnostic in diagnostics:
        console.print(
            f"{indent}  - {getattr(diagnostic, 'code')}: {getattr(diagnostic, 'message')}"
        )
        suggested = getattr(diagnostic, "suggested_command", "")
        if suggested:
            console.print(f"{indent}    command: {suggested}")
