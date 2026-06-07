from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_next_commands(next_app: typer.Typer) -> None:
    @next_app.callback(invoke_without_command=True)
    def next_action(
        ctx: typer.Context,
        top: int | None = typer.Option(None, "--top", min=1, help="Limit the number of actions shown"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show advisory next actions."""
        if ctx.invoked_subcommand is not None:
            return
        try:
            actions = workspace_for(root).next_actions(limit=top)
        except ValueError as exc:
            fail(str(exc))
        _print_next_actions(actions)

    @next_app.command("list")
    def next_list(
        top: int | None = typer.Option(None, "--top", min=1, help="Limit the number of actions shown"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List curated and generated next actions."""
        try:
            actions = workspace_for(root).next_actions(limit=top)
        except ValueError as exc:
            fail(str(exc))
        _print_next_actions(actions)

    @next_app.command("add")
    def next_add(
        kind: str = typer.Argument(..., help="Action kind, e.g. verify_integration"),
        target: str = typer.Argument("", help="Action target"),
        reason: str = typer.Option(..., "--reason", help="Why this action is needed"),
        command: str = typer.Option("", "--command", help="Suggested command or instruction"),
        priority: str = typer.Option("medium", "--priority", help="Priority: high, medium, low"),
        action_id: str | None = typer.Option(None, "--id", help="Optional explicit NEXT-XXX ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Add a curated next action."""
        try:
            action = workspace_for(root).next_action_add(
                kind=kind,
                target=target,
                reason=reason,
                command=command,
                priority=priority,
                action_id=action_id,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Next action added.[/green]")
        console.print(f"  id: {action.action_id}")
        console.print(f"  kind: {action.kind}")
        console.print(f"  target: {action.target or 'none'}")

    @next_app.command("complete")
    def next_complete(
        action_id: str = typer.Argument(..., help="Next action ID, e.g. NEXT-003"),
        reason: str = typer.Option(..., "--reason", help="Completion reason"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Complete a curated next action and move it to the audit log."""
        try:
            result = workspace_for(root).next_action_complete(action_id, reason)
        except ValueError as exc:
            fail(str(exc))
        action = result["action"]
        console.print("[green]Next action completed.[/green]")
        console.print(f"  id: {action.get('id')}")
        console.print(f"  log: {result['path']}")

    @next_app.command("retire")
    def next_retire(
        action_id: str = typer.Argument(..., help="Next action ID, e.g. NEXT-003"),
        reason: str = typer.Option(..., "--reason", help="Retirement reason"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Retire a curated next action and move it to the audit log."""
        try:
            result = workspace_for(root).next_action_retire(action_id, reason)
        except ValueError as exc:
            fail(str(exc))
        action = result["action"]
        console.print("[green]Next action retired.[/green]")
        console.print(f"  id: {action.get('id')}")
        console.print(f"  log: {result['path']}")

    @next_app.command("refresh")
    def next_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Normalize curated next actions and report generated action count."""
        try:
            result = workspace_for(root).next_actions_refresh()
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Next actions refreshed.[/green]")
        console.print(f"  active_curated: {result['active_curated']}")
        console.print(f"  generated: {result['generated']}")
        console.print(f"  path: {result['path']}")


def _print_next_actions(actions: list[object]) -> None:
    console.print("Next actions")
    if not actions:
        console.print("  none")
        return
    for index, action in enumerate(actions, start=1):
        target = f"  target: {getattr(action, 'target')}" if getattr(action, "target") else "  target: none"
        console.print(
            f"{index}. {getattr(action, 'action_id')}  {getattr(action, 'priority')}  {getattr(action, 'kind')}"
        )
        console.print(target)
        console.print(f"  reason: {getattr(action, 'reason')}")
        console.print(f"  command: {getattr(action, 'command') or 'none'}")
        console.print(f"  source: {getattr(action, 'source')}")
