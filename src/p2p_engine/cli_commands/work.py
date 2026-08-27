from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.cli_shared import yaml_dump_for_cli


def register_work_commands(work_app: typer.Typer) -> None:
    @work_app.command("plan")
    def work_plan(
        change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
        target: str = typer.Option(
            ...,
            "--target",
            help="Validated export target: generic, openspec, or speckit",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create a logical P2P Work handoff manifest."""
        try:
            work = workspace_for(root).create_work_plan(change, target)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Work plan created.[/green]")
        console.print(f"  work: {work.work_id}")
        console.print(f"  status: {work.status}")
        console.print(f"  change: {work.change_id}")
        console.print(f"  target: {work.target}")
        console.print(f"  path: {work.path}")

    @work_app.command("list")
    def work_list(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List P2P Work manifests."""
        works = workspace_for(root).work_statuses()
        console.print("Work items")
        if not works:
            console.print("  none")
            return
        for work in works:
            console.print(
                f"  {work.work_id}  {work.status}  {work.change_id}  {work.target}"
            )

    @work_app.command("status")
    def work_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a read-only summary of logical P2P Work items."""
        works = workspace_for(root).work_summaries()
        console.print("Work status")
        if not works:
            console.print("  none")
            return
        for work in works:
            console.print(f"{work.work_id}  {work.status}")
            console.print(f"  change: {work.change_id}")
            console.print(f"  target: {work.target}")
            console.print(f"  next: {work.next_action}")
            console.print(f"  note: {work.note}")

    @work_app.command("retire")
    def work_retire(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        reason: str = typer.Option(..., "--reason", help="Why this Work item is obsolete"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Retire an obsolete planned Work manifest."""
        try:
            retired = workspace_for(root).retire_work(work_id, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Work retired.[/green]")
        console.print(f"  work: {retired.work_id}")
        console.print(f"  status: {retired.status}")
        console.print(f"  reason: {retired.reason}")
        console.print(f"  path: {retired.path}")

    @work_app.command("show")
    def work_show(
        work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a P2P Work manifest."""
        try:
            work = workspace_for(root).show_work(work_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"{work.work_id} - {work.status}")
        console.print(f"  change: {work.change_id}")
        console.print(f"  target: {work.target}")
        console.print(f"  path: {work.path}")
        console.print(yaml_dump_for_cli(work.manifest))
