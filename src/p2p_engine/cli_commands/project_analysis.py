from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_project_analysis_commands(
    impact_app: typer.Typer,
    conflict_app: typer.Typer,
) -> None:
    @impact_app.command("prompt")
    def impact_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate an impact-analysis prompt file."""
        try:
            path = workspace_for(root).generate_prompt(proposal_id, "impact")
        except ValueError as exc:
            fail(str(exc))
        console.print(f"[green]Generated[/green] {path}")

    @impact_app.command("import")
    def impact_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Impact output file or artifact directory"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import impact artifacts into a proposal."""
        try:
            imported = workspace_for(root).import_impact(proposal_id, source)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Impact imported.[/green]")
        for path in imported:
            console.print(f"  updated {path}")

    @conflict_app.command("record")
    def conflict_record(
        proposal_ids: list[str] = typer.Argument(..., help="Two or more proposal IDs"),
        conflict_type: str = typer.Option("overlaps", "--type", help="Conflict relationship type"),
        reason: str = typer.Option(..., "--reason", help="Why these proposals conflict or overlap"),
        winner: str | None = typer.Option(None, "--winner", help="Winning proposal if decided"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record conflict memory in .p2p/project/conflicts.yml."""
        try:
            status = workspace_for(root).record_conflict(
                proposals=proposal_ids,
                conflict_type=conflict_type,
                reason=reason,
                winner=winner,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Conflict recorded.[/green]")
        console.print(f"  conflicts: {status.conflicts_count}")
        console.print(f"  file: {status.conflicts_file}")

    @conflict_app.command("status")
    def conflict_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show recorded project conflicts."""
        try:
            status = workspace_for(root).conflict_status()
        except ValueError as exc:
            fail(str(exc))
        console.print("Project conflicts")
        console.print(f"  file: {status.conflicts_file}")
        if not status.conflicts:
            console.print("  conflicts: none")
            return
        for conflict in status.conflicts:
            proposals = ", ".join(str(item) for item in conflict.get("proposals", []))
            console.print(f"  {conflict.get('id')}: {conflict.get('type')} [{proposals}]")
