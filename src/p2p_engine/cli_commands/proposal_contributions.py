from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.contribution import (
    ContributionType,
    allowed_contribution_type_text,
    parse_contribution_type,
)


CONTRIBUTION_TYPE_HELP = f"Contribution type. Allowed: {allowed_contribution_type_text()}"


def register_proposal_contribution_commands(
    proposal_app: typer.Typer,
    proposal_contribution_app: typer.Typer,
    contribution_app: typer.Typer,
) -> None:
    @contribution_app.command("add")
    def contribution_add(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        text: str = typer.Argument(..., help="Contribution text"),
        contribution_type: str = typer.Option(
            ContributionType.suggestion.value,
            "--type",
            help=CONTRIBUTION_TYPE_HELP,
        ),
        relevance: str = typer.Option("medium", "--relevance", help="Relevance hint"),
        author: str = typer.Option("local", "--author", help="Contribution author"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Append a contribution to a proposal."""
        workspace = workspace_for(root)
        try:
            contribution = workspace.add_contribution(
                proposal_id=proposal_id,
                contribution_type=parse_contribution_type(contribution_type),
                text=text,
                relevance_hint=relevance,
                author=author,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Contribution added.[/green]")
        console.print(f"  id: {contribution.contribution_id}")
        console.print(f"  proposal: {proposal_id}")

    @proposal_contribution_app.command("add")
    def proposal_contribution_add(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        text: str = typer.Argument(..., help="Contribution text"),
        contribution_type: str = typer.Option(
            ContributionType.suggestion.value,
            "--type",
            help=CONTRIBUTION_TYPE_HELP,
        ),
        relevance: str = typer.Option("medium", "--relevance", help="Relevance hint"),
        author: str = typer.Option("local", "--author", help="Contribution author"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Append a contribution to a proposal."""
        contribution_add(
            proposal_id=proposal_id,
            text=text,
            contribution_type=contribution_type,
            relevance=relevance,
            author=author,
            root=root,
        )

    @contribution_app.command("list")
    def contribution_list(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List contributions for a proposal."""
        try:
            contributions = workspace_for(root).list_contributions(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        _print_contribution_list(contributions)

    @proposal_contribution_app.command("list")
    def proposal_contribution_list(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List contributions for a proposal."""
        contribution_list(proposal_id=proposal_id, root=root)

    @proposal_app.command("contributions")
    def proposal_contributions(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List contributions for a proposal."""
        contribution_list(proposal_id=proposal_id, root=root)


def _print_contribution_list(contribution_list: object) -> None:
    console.print(f"Proposal contributions for [bold]{getattr(contribution_list, 'proposal_id')}[/bold]")
    console.print(f"  path: {getattr(contribution_list, 'path')}")
    contributions = getattr(contribution_list, "contributions")
    if not contributions:
        console.print("  none")
        return
    for contribution in contributions:
        console.print(f"  {contribution.contribution_id}  {contribution.contribution_type.value}  {contribution.author}")
        console.print(f"    relevance: {contribution.relevance_hint}")
        console.print(f"    text: {contribution.text}")
