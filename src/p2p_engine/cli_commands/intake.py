from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_intake_commands(
    intake_app: typer.Typer,
    intake_apply_app: typer.Typer,
) -> None:
    @intake_app.command("prompt")
    def intake_prompt(
        idea: str = typer.Argument(..., help="Raw idea or observation to analyze"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create an intake prompt backed by generated project registries."""
        try:
            prompt = workspace_for(root).create_intake_prompt(idea)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Intake prompt created.[/green]")
        console.print(f"  id: {prompt.intake_id}")
        console.print(f"  path: {prompt.path}")
        console.print(f"  prompt: {prompt.prompt_path}")

    @intake_app.command("import")
    def intake_import(
        intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
        source: Path = typer.Argument(..., help="File or directory containing intake output"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import human or AI intake analysis output."""
        try:
            imported = workspace_for(root).import_intake(intake_id, source)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Intake imported.[/green]")
        for path in imported:
            console.print(f"  updated {path}")

    @intake_app.command("status")
    def intake_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List intake records and analysis state."""
        try:
            statuses = workspace_for(root).intake_statuses()
        except ValueError as exc:
            fail(str(exc))
        console.print("Intake records")
        if not statuses:
            console.print("  none")
            return
        for status in statuses:
            console.print(f"  {status.intake_id}  {status.status}  {status.path}")

    @intake_apply_app.command("plan")
    def intake_apply_plan(
        intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create a controlled intake apply plan."""
        try:
            plan = workspace_for(root).create_intake_apply_plan(intake_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Intake apply plan created.[/green]")
        console.print(f"  intake: {plan.intake_id}")
        console.print(f"  path: {plan.path}")
        console.print(f"  actions: {len(plan.actions)}")

    @intake_apply_app.command("show")
    def intake_apply_show(
        intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a controlled intake apply plan."""
        try:
            plan = workspace_for(root).show_intake_apply_plan(intake_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"Intake apply plan {plan.intake_id}")
        console.print(f"  path: {plan.path}")
        if not plan.actions:
            console.print("  actions: none")
            return
        for action in plan.actions:
            console.print(
                f"  {action.get('id')}  {action.get('status')}  "
                f"{action.get('support')}  {action.get('type')} -> {action.get('target')}"
            )
            console.print(f"    reason: {action.get('reason') or ''}")
            console.print(f"    command: {action.get('command_preview') or 'none'}")

    @intake_apply_app.command("run")
    def intake_apply_run(
        intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
        action: str = typer.Option(..., "--action", help="Apply action ID, e.g. APPLY-001"),
        option: list[str] | None = typer.Option(None, "--option", help="Choice option. Can be repeated."),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Run one explicit supported intake apply action."""
        try:
            applied = workspace_for(root).run_intake_apply_action(intake_id, action, option)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Intake apply action applied.[/green]")
        console.print(f"  id: {applied.applied_id}")
        console.print(f"  action: {applied.plan_action}")
        console.print(f"  type: {applied.action_type}")
        console.print(f"  target: {applied.target}")
        console.print(f"  log: {applied.path}")
