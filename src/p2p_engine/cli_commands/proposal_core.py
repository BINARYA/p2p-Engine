from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_proposal_core_commands(proposal_app: typer.Typer) -> None:
    @proposal_app.command("create")
    def proposal_create(
        title: str = typer.Argument(..., help="Proposal title"),
        problem: str | None = typer.Option(None, "--problem", help="Problem statement"),
        context: str | None = typer.Option(None, "--context", help="Proposal context"),
        goal: list[str] | None = typer.Option(None, "--goal", help="Goal. Can be repeated."),
        non_goal: list[str] | None = typer.Option(None, "--non-goal", help="Non-goal. Can be repeated."),
        proposal_text: str | None = typer.Option(None, "--proposal", help="Proposed direction"),
        acceptance: list[str] | None = typer.Option(
            None,
            "--acceptance",
            help="Acceptance criterion. Can be repeated.",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create a proposal scaffold."""
        workspace = workspace_for(root)
        try:
            proposal = workspace.create_proposal_with_details(
                title=title,
                problem=problem,
                context=context,
                goals=goal,
                non_goals=non_goal,
                proposal=proposal_text,
                acceptance_criteria=acceptance,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal created.[/green]")
        console.print(f"  id: {proposal.proposal_id}")
        console.print(f"  slug: {proposal.slug}")
        console.print(f"  path: {proposal.path}")

    @proposal_app.command("update")
    def proposal_update(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        problem: str | None = typer.Option(None, "--problem", help="Problem statement"),
        context: str | None = typer.Option(None, "--context", help="Proposal context"),
        goal: list[str] | None = typer.Option(None, "--goal", help="Goal. Can be repeated."),
        non_goal: list[str] | None = typer.Option(None, "--non-goal", help="Non-goal. Can be repeated."),
        proposal_text: str | None = typer.Option(None, "--proposal", help="Proposed direction"),
        acceptance: list[str] | None = typer.Option(
            None,
            "--acceptance",
            help="Acceptance criterion. Can be repeated.",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Update structured sections in proposal.md."""
        try:
            path = workspace_for(root).update_proposal(
                proposal_id=proposal_id,
                problem=problem,
                context=context,
                goals=goal,
                non_goals=non_goal,
                proposal=proposal_text,
                acceptance_criteria=acceptance,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print(f"[green]Updated[/green] {path}")

    @proposal_app.command("list")
    def proposal_list(
        status_filter: str | None = typer.Option(None, "--status", help="Filter by proposal status"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List proposals with stable, agent-friendly output."""
        proposals = workspace_for(root).proposal_summaries(status=status_filter)
        console.print("Proposals")
        if not proposals:
            console.print("  none")
            return
        for proposal in proposals:
            console.print(f"  {proposal.proposal_id}  {proposal.status}  {proposal.title}")

    @proposal_app.command("show")
    def proposal_show(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a compact proposal summary."""
        try:
            proposal = workspace_for(root).show_proposal(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"{proposal.proposal_id} - [bold]{proposal.title}[/bold]")
        console.print(f"  status: {proposal.status}")
        console.print(f"  path: {proposal.path}")
        console.print("")
        console.print("Problem:")
        console.print(proposal.problem)
        console.print("")
        console.print("Proposal:")
        console.print(proposal.proposal)
        console.print("")
        console.print("Decision:")
        console.print(f"  status: {proposal.decision_status}")
        console.print(f"  reason: {proposal.decision_reason}")
