from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_proposal_readiness_commands(proposal_readiness_app: typer.Typer) -> None:
    @proposal_readiness_app.command("show")
    def proposal_readiness_show(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show proposal readiness status."""
        try:
            readiness = workspace_for(root).read_proposal_readiness(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_proposal_readiness(readiness)

    @proposal_readiness_app.command("refresh")
    def proposal_readiness_refresh(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Refresh proposal readiness snapshot."""
        try:
            readiness = workspace_for(root).refresh_proposal_readiness(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal readiness refreshed.[/green]")
        print_proposal_readiness(readiness)
        if getattr(readiness, "status") == "not_assessed":
            console.print(f"  suggested_next: p2p proposal readiness init {proposal_id}")

    @proposal_readiness_app.command("init")
    def proposal_readiness_init(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Bootstrap proposal readiness from available proposal artifacts."""
        try:
            readiness = workspace_for(root).initialize_proposal_readiness(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal readiness initialized.[/green]")
        print_proposal_readiness(readiness, explain=True)

    @proposal_readiness_app.command("explain")
    def proposal_readiness_explain(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Explain proposal readiness gaps and next actions."""
        try:
            readiness = workspace_for(root).read_proposal_readiness(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_proposal_readiness(readiness, explain=True)


def print_proposal_readiness(readiness: object, *, explain: bool = False) -> None:
    console.print(f"Proposal readiness for [bold]{getattr(readiness, 'proposal_id')}[/bold]")
    console.print(f"  status: {getattr(readiness, 'status')}")
    console.print(f"  path: {getattr(readiness, 'path')}")
    console.print(f"  profile: {getattr(readiness, 'profile_id') or 'none'}")
    console.print(f"  profile_version: {getattr(readiness, 'profile_version') or 'none'}")
    console.print(f"  computed_score: {getattr(readiness, 'computed_score') if getattr(readiness, 'computed_score') is not None else 'none'}")
    console.print(f"  computed_label: {getattr(readiness, 'computed_label') or 'none'}")
    console.print(f"  confidence: {getattr(readiness, 'confidence') or 'none'}")
    if explain:
        failed_gates = getattr(readiness, "failed_gates")
        missing = getattr(readiness, "missing")
        suggested_next = getattr(readiness, "suggested_next")
        console.print("  failed_gates:")
        if failed_gates:
            for gate in failed_gates:
                console.print(f"    - {gate}")
        else:
            console.print("    none")
        console.print("  missing:")
        if missing:
            for item in missing:
                console.print(f"    - {item}")
        else:
            console.print("    none")
        console.print("  suggested_next:")
        if suggested_next:
            for item in suggested_next:
                console.print(f"    - {item}")
        else:
            console.print("    none")
