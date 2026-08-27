from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_change_commands(change_app: typer.Typer) -> None:
    @change_app.command("create")
    def change_create(
        source: str = typer.Option(..., "--from", help="Accepted proposal ID, e.g. PROP-013"),
        title: str | None = typer.Option(None, "--title", help="Optional Change Set title"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create metadata-only Change Set from accepted project intent."""
        try:
            change = workspace_for(root).create_change_set(source=source, title=title)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Change Set created.[/green]")
        console.print(f"  id: {change.change_id}")
        console.print(f"  status: {change.status}")
        console.print(f"  path: {change.path}")

    @change_app.command("status")
    def change_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List Change Sets and lifecycle states."""
        changes = workspace_for(root).change_set_statuses()
        console.print("Change Sets")
        if not changes:
            console.print("  none")
            return
        for change in changes:
            console.print(f"  {change.change_id}  {change.status}  {change.title}")

    @change_app.command("show")
    def change_show(
        change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a Change Set summary."""
        try:
            change = workspace_for(root).show_change_set(change_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"{change.change_id} - [bold]{change.title}[/bold]")
        console.print(f"  status: {change.status}")
        console.print(f"  path: {change.path}")
        console.print(f"  execution_domains: {', '.join(change.execution_domains) or 'none'}")
        console.print(f"  implementation_targets: {', '.join(change.implementation_targets) or 'none'}")
        console.print(f"  spec_targets: {', '.join(change.spec_targets) or 'none'}")
        console.print(f"  export_targets: {', '.join(change.export_targets) or 'none'}")
        console.print(f"  plan: {change.plan_ref}")
        console.print(f"  tasks: {change.tasks_ref}")
        console.print("")
        console.print(change.summary)

    @change_app.command("set-status")
    def change_set_status(
        change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
        status: str = typer.Argument(..., help="New lifecycle status"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Update a Change Set lifecycle status."""
        try:
            change = workspace_for(root).update_change_set_status(change_id, status)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Change Set status updated.[/green]")
        console.print(f"  id: {change.change_id}")
        console.print(f"  status: {change.status}")

    @change_app.command("tasks")
    def change_tasks(
        change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show Change Set tasks and actions."""
        try:
            view = workspace_for(root).change_set_tasks(change_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"Tasks for [bold]{view.change_id}[/bold]")
        if not view.tasks:
            console.print("  tasks: none")
        else:
            for task in view.tasks:
                console.print(f"  {task.get('id', '-')}: {task.get('status', 'unknown')}  {task.get('title', '')}")
        if not view.actions:
            console.print("  actions: none")
        else:
            console.print("Actions:")
            for action in view.actions:
                checked = "x" if action.get("checked") else " "
                console.print(
                    f"  [{checked}] {action.get('id', '-')}: {action.get('title', '')}",
                    markup=False,
                )
