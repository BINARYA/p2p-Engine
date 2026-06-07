from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.decision import DecisionOutcome


def register_proposal_decision_commands(
    proposal_app: typer.Typer,
    decision_app: typer.Typer,
) -> None:
    @proposal_app.command("accept")
    def proposal_accept(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Decision reason"),
        approver: str = typer.Option("local", "--approver", help="Decision approver"),
        override_readiness: bool = typer.Option(
            False,
            "--override-readiness",
            help="Record an explicit owner readiness override while accepting.",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Accept a proposal."""
        workspace = workspace_for(root)
        try:
            readiness = workspace.read_proposal_readiness(proposal_id)
            if override_readiness:
                override_path = workspace.record_proposal_readiness_override(
                    proposal_id=proposal_id,
                    reason=reason,
                    approver=approver,
                )
                console.print("[yellow]Readiness override recorded.[/yellow]")
                console.print(f"  readiness: {override_path}")
            elif (
                readiness.status == "not_assessed"
                or readiness.computed_score is None
                or readiness.computed_score < 85
                or bool(readiness.failed_gates)
            ):
                console.print(
                    "[yellow]Warning: accepting without decision-ready proposal readiness. "
                    "Use --override-readiness to record an explicit owner override.[/yellow]"
                )
        except ValueError as exc:
            fail(str(exc))
        _record_proposal_decision(proposal_id, DecisionOutcome.accepted, reason, approver, root)

    @proposal_app.command("reject")
    def proposal_reject(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Decision reason"),
        approver: str = typer.Option("local", "--approver", help="Decision approver"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Reject a proposal."""
        _record_proposal_decision(proposal_id, DecisionOutcome.rejected, reason, approver, root)

    @proposal_app.command("defer")
    def proposal_defer(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Decision reason"),
        approver: str = typer.Option("local", "--approver", help="Decision approver"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Defer a proposal."""
        _record_proposal_decision(proposal_id, DecisionOutcome.deferred, reason, approver, root)

    @decision_app.command("record")
    def decision_record(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        outcome: DecisionOutcome = typer.Option(..., "--outcome", help="Decision outcome"),
        reason: str = typer.Option(..., "--reason", help="Decision reason"),
        approver: str = typer.Option("local", "--approver", help="Decision approver"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record a decision for a proposal."""
        workspace = workspace_for(root)
        try:
            decision = workspace.record_decision(
                proposal_id=proposal_id,
                outcome=outcome,
                reason=reason,
                approver=approver,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Decision recorded.[/green]")
        console.print(f"  proposal: {proposal_id}")
        console.print(f"  outcome: {decision.outcome.value}")


def _record_proposal_decision(
    proposal_id: str,
    outcome: DecisionOutcome,
    reason: str,
    approver: str,
    root: Path,
) -> None:
    workspace = workspace_for(root)
    try:
        decision = workspace.record_decision(
            proposal_id=proposal_id,
            outcome=outcome,
            reason=reason,
            approver=approver,
        )
    except ValueError as exc:
        fail(str(exc))
    console.print("[green]Proposal decision recorded.[/green]")
    console.print(f"  proposal: {proposal_id}")
    console.print(f"  outcome: {decision.outcome.value}")
