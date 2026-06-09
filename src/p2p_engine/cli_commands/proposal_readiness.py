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
        elif _needs_review_guidance(readiness):
            console.print("  guidance: refresh is conservative; evidence-aware review or proposal questions may be needed.")
            console.print(f"  suggested_next: p2p proposal questions status {proposal_id}")
            console.print(f"  suggested_next: p2p proposal questions next {proposal_id}")
            console.print(f"  suggested_next: p2p proposal readiness explain {proposal_id}")

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

    @proposal_readiness_app.command("assess")
    def proposal_readiness_assess(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Recalculate proposal readiness from current artifacts and question state."""
        try:
            readiness = workspace_for(root).assess_proposal_readiness(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal readiness assessed.[/green]")
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

    @proposal_readiness_app.command("review")
    def proposal_readiness_review(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Review readiness gaps and proactive question guidance."""
        try:
            review = workspace_for(root).review_proposal_readiness(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_readiness_review(review)


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


def _needs_review_guidance(readiness: object) -> bool:
    score = getattr(readiness, "computed_score")
    failed_gates = getattr(readiness, "failed_gates")
    missing = getattr(readiness, "missing")
    confidence = getattr(readiness, "confidence")
    return (
        score is None
        or score < 85
        or bool(failed_gates)
        or bool(missing)
        or confidence == "low"
    )


def print_readiness_review(review: object) -> None:
    console.print(f"Proposal readiness review for [bold]{getattr(review, 'proposal_id')}[/bold]")
    console.print(f"  question_state: {getattr(review, 'question_state_status')}")
    for label in (
        "challenge_points",
        "owner_questions",
        "thin_artifact_warnings",
        "alternative_prompts",
        "tradeoff_prompts",
        "acceptance_cautions",
        "assertiveness_guidance",
        "merge_candidates",
        "suggested_next",
    ):
        console.print(f"  {label}:")
        values = getattr(review, label)
        if values:
            for value in values:
                console.print(f"    - {value}")
        else:
            console.print("    none")
