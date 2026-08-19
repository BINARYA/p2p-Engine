from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import contract_failure, print_json
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
        operation_key: str = typer.Option("", "--operation-key"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Recalculate proposal readiness from current artifacts and question state."""
        json_output = _wants_json(output_format)
        if json_output and not operation_key.strip():
            contract_failure(
                "P2P_IDEMPOTENCY_KEY_REQUIRED: JSON readiness assessment requires --operation-key",
                code="P2P_IDEMPOTENCY_KEY_REQUIRED",
            )
        if operation_key.strip() and not json_output:
            fail(
                "P2P_PROPOSAL_READINESS_ASSESS_OPERATION_KEY_REQUIRES_JSON: "
                "--operation-key requires --format json"
            )
        try:
            if json_output:
                print_json(
                    workspace_for(root).assess_proposal_readiness_with_operation_key(
                        proposal_id=proposal_id,
                        operation_key=operation_key,
                        actor=actor,
                    )
                )
                return
            readiness = workspace_for(root).assess_proposal_readiness(
                proposal_id,
                actor=actor,
            )
        except ValueError as exc:
            if json_output:
                message = str(exc)
                contract_failure(message, code=_readiness_error_code(message))
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
    console.print(f"  freshness: {getattr(readiness, 'freshness', 'not_assessed')}")
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
        _print_owner_question_state(getattr(readiness, "owner_question_state", {}) or {}, indent="  ")


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


def _wants_json(output_format: str) -> bool:
    normalized = output_format.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized == "json"


def _readiness_error_code(message: str) -> str:
    prefix = message.split(":", 1)[0]
    if prefix.startswith("P2P_"):
        return prefix
    if message.startswith("Proposal not found:") or message == "No .p2p/proposals directory found.":
        return "P2P_PROPOSAL_NOT_FOUND"
    if message.startswith("Ambiguous proposal ID:"):
        return "P2P_PROPOSAL_AMBIGUOUS_ID"
    if message.startswith("Readiness profile not found:"):
        return "P2P_READINESS_PROFILE_NOT_FOUND"
    return "P2P_PROPOSAL_READINESS_ASSESS_FAILED"


def print_readiness_review(review: object) -> None:
    console.print(f"Proposal readiness review for [bold]{getattr(review, 'proposal_id')}[/bold]")
    console.print(f"  question_state: {getattr(review, 'question_state_status')}")
    _print_owner_question_state(getattr(review, "owner_question_state", {}) or {}, indent="  ")
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


def _print_owner_question_state(owner_question_state: dict[str, object], *, indent: str) -> None:
    if not owner_question_state:
        return
    console.print(f"{indent}owner_question_state:")
    console.print(f"{indent}  source: {owner_question_state.get('source') or 'none'}")
    for key in (
        "blocking_owner_questions",
        "answered_not_applied",
        "residual_follow_up",
        "closed_questions",
    ):
        console.print(f"{indent}  {key}:")
        values = owner_question_state.get(key) or []
        if values:
            for item in values:
                if isinstance(item, dict):
                    console.print(
                        f"{indent}    - {item.get('id')} "
                        f"{item.get('priority')}/{item.get('state')}: {item.get('reason')}"
                    )
                else:
                    console.print(f"{indent}    - {item}")
        else:
            console.print(f"{indent}    none")
    notes = owner_question_state.get("confidence_notes") or []
    if notes:
        console.print(f"{indent}  confidence_notes:")
        for item in notes:
            console.print(f"{indent}    - {item}")
