from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.cli_commands.formatting import emit_structured


def register_governance_commands(
    governance_app: typer.Typer,
    vote_app: typer.Typer,
    precedent_app: typer.Typer,
) -> None:
    @governance_app.command("init")
    def governance_init(
        mode: str = typer.Option(
            "owner_decides",
            "--mode",
            help="Governance mode: owner_decides, open_consensus, or exclusive_vote",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Initialize file-based governance artifacts."""
        try:
            created = workspace_for(root).init_governance(mode)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Governance initialized.[/green]")
        for path in created:
            console.print(f"  updated {path}")

    @governance_app.command("status")
    def governance_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text, json, or yaml"),
    ) -> None:
        """Show governance mode and audit artifacts."""
        status = workspace_for(root).governance_status()
        if emit_structured(status, output_format):
            return
        console.print("Governance status")
        console.print(f"  mode: {status.mode}")
        console.print(f"  roles: {status.roles_count}")
        console.print(f"  precedents: {status.precedents_count}")
        console.print(f"  file: {status.governance_file}")

    @governance_app.command("validate")
    def governance_validate(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text, json, or yaml"),
    ) -> None:
        """Validate governance artifacts without mutating project state."""
        result = workspace_for(root).validate_governance_policy()
        if emit_structured(result, output_format):
            if not result.ok:
                raise typer.Exit(1)
            return
        console.print("Governance validation")
        if not result.findings:
            console.print("  ok")
            return
        for finding in result.findings:
            console.print(f"  {finding.severity}: {finding.code} {finding.path}")
            console.print(f"    {finding.message}")
            if finding.suggested_command:
                console.print(f"    command: {finding.suggested_command}")
        if not result.ok:
            raise typer.Exit(1)

    @vote_app.command("record")
    def vote_record(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        choice: str = typer.Option(..., "--choice", help="Chosen alternative ID or label"),
        reason: str = typer.Option(..., "--reason", help="Reason for the vote"),
        voter: str = typer.Option("local", "--voter", help="Voter identifier"),
        role: str = typer.Option("contributor", "--role", help="Governance role"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record a governance vote in votes.yml."""
        try:
            status = workspace_for(root).record_vote(
                proposal_id=proposal_id,
                choice=choice,
                reason=reason,
                voter=voter,
                role=role,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Vote recorded.[/green]")
        console.print(f"  proposal: {status.proposal_id}")
        console.print(f"  total votes: {status.total_votes}")
        if status.tied:
            console.print("  current result: tied")
        elif status.winner:
            console.print(f"  current winner: {status.winner}")
        else:
            console.print("  current winner: none")

    @vote_app.command("status")
    def vote_status(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text, json, or yaml"),
    ) -> None:
        """Show vote counts for a proposal."""
        try:
            status = workspace_for(root).vote_status(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        if emit_structured(status, output_format):
            return
        console.print(f"Vote status for [bold]{status.proposal_id}[/bold]")
        if not status.counts:
            console.print("  votes: none")
            return
        for choice, count in sorted(status.counts.items()):
            console.print(f"  {choice}: {count}")
        if status.tied:
            console.print("  result: tied")
        elif status.winner:
            console.print(f"  result: {status.winner}")

    @precedent_app.command("record")
    def precedent_record(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        title: str = typer.Option(..., "--title", help="Precedent title"),
        reason: str = typer.Option(..., "--reason", help="Why this should prevent repeated debate"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record a reusable decision precedent."""
        try:
            path = workspace_for(root).record_precedent(proposal_id, title, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"[green]Precedent recorded[/green] {path}")

    @precedent_app.command("search")
    def precedent_search(
        precedent_id: str | None = typer.Option(None, "--precedent", help="Explicit precedent ID"),
        proposal_id: str | None = typer.Option(None, "--proposal", help="Related proposal ID"),
        choice_id: str | None = typer.Option(None, "--choice", help="Related choice ID"),
        tag: str | None = typer.Option(None, "--tag", help="Explicit precedent tag"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text, json, or yaml"),
    ) -> None:
        """Search deterministic governance precedents without recording new ones."""
        try:
            matches = workspace_for(root).search_decision_precedents(
                precedent_id=precedent_id,
                proposal_id=proposal_id,
                choice_id=choice_id,
                tag=tag,
            )
        except ValueError as exc:
            fail(str(exc))
        if emit_structured({"precedents": matches}, output_format):
            return
        console.print("Decision precedents")
        if not matches:
            console.print("  none")
            return
        for match in matches:
            console.print(f"  {match.precedent_id}  {match.match_reason}  {match.related_target}")
            if match.title:
                console.print(f"    title: {match.title}")
            console.print(f"    source: {match.source}")
