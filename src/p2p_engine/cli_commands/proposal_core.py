from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import contract_failure, print_json
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
        operation_key: str = typer.Option("", "--operation-key"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Create a proposal scaffold."""
        workspace = workspace_for(root)
        json_output = _wants_json(output_format)
        _validate_operation_key_mode(
            operation_key,
            json_output=json_output,
            operation="proposal_create",
        )
        try:
            if json_output:
                print_json(
                    workspace.create_proposal_with_operation_key(
                        title=title,
                        operation_key=operation_key,
                        actor=actor,
                        problem=problem,
                        context=context,
                        goals=goal,
                        non_goals=non_goal,
                        proposal=proposal_text,
                        acceptance_criteria=acceptance,
                    )
                )
                return
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
            _fail_proposal_operation(exc, output_format=output_format)
        console.print("[green]Proposal created.[/green]")
        console.print(f"  id: {proposal.proposal_id}")
        console.print(f"  slug: {proposal.slug}")
        console.print(f"  path: {proposal.path}")
        console.print("")
        console.print("Next canonical P2P commands:")
        console.print(f"  p2p proposal show {proposal.proposal_id}")
        console.print(f"  p2p contribution add {proposal.proposal_id} \"...\" --type finding")
        console.print(f"  p2p explore prompt {proposal.proposal_id}")
        console.print(f"  p2p proposal readiness init {proposal.proposal_id}")
        console.print(f"  p2p proposal questions init {proposal.proposal_id}")

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
        operation_key: str = typer.Option("", "--operation-key"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Update structured sections in proposal.md."""
        json_output = _wants_json(output_format)
        _validate_operation_key_mode(
            operation_key,
            json_output=json_output,
            operation="proposal_update",
        )
        try:
            if json_output:
                print_json(
                    workspace_for(root).update_proposal_with_operation_key(
                        proposal_id=proposal_id,
                        operation_key=operation_key,
                        actor=actor,
                        problem=problem,
                        context=context,
                        goals=goal,
                        non_goals=non_goal,
                        proposal=proposal_text,
                        acceptance_criteria=acceptance,
                    )
                )
                return
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
            _fail_proposal_operation(exc, output_format=output_format)
        console.print(f"[green]Updated[/green] {path}")

    @proposal_app.command("list")
    def proposal_list(
        status_filter: str | None = typer.Option(None, "--status", help="Filter by proposal status"),
        decision_state: str | None = typer.Option(
            None,
            "--decision-state",
            help="Filter by effective decision state",
        ),
        limit: int = typer.Option(50, "--limit", min=1, max=100),
        offset: int = typer.Option(0, "--offset", min=0),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List proposals with stable, agent-friendly output."""
        workspace = workspace_for(root)
        if _wants_json(output_format):
            try:
                payload = workspace.proposal_list_contract(
                    status=status_filter,
                    decision_state=decision_state,
                    limit=limit,
                    offset=offset,
                )
            except ValueError as exc:
                _fail_proposal_operation(exc, output_format=output_format)
            print_json({"proposal_list": payload})
            return
        proposals = workspace.proposal_summaries(status=status_filter)
        if decision_state is not None:
            proposals = [
                proposal
                for proposal in proposals
                if proposal.effective_state == decision_state
            ]
        proposals = proposals[offset : offset + limit]
        console.print("Proposals")
        if not proposals:
            console.print("  none")
            return
        for proposal in proposals:
            console.print(f"  {proposal.proposal_id}  {proposal.status}  {proposal.title}")

    @proposal_app.command("show")
    def proposal_show(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        full: bool = typer.Option(False, "--full", help="Show owner-facing full proposal view"),
        limit: int = typer.Option(50, "--limit", min=1, max=100),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show a compact proposal summary."""
        workspace = workspace_for(root)
        try:
            if _wants_json(output_format):
                print_json(
                    {
                        "proposal_detail": workspace.proposal_detail_contract(
                            proposal_id,
                            contribution_limit=limit,
                        )
                    }
                )
                return
            if full:
                _print_full_proposal_view(workspace.proposal_full_view(proposal_id))
                return
            proposal = workspace.show_proposal(proposal_id)
        except ValueError as exc:
            _fail_proposal_operation(exc, output_format=output_format)
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


def _print_full_proposal_view(view: object) -> None:
    console.print(f"Full proposal view for {getattr(view, 'proposal_id')} - [bold]{getattr(view, 'title')}[/bold]")
    console.print(f"  status: {getattr(view, 'status')}")
    console.print(f"  source: {getattr(view, 'path')} (evidence)")
    console.print("")

    console.print("Proposal Body:")
    sections = getattr(view, "core_sections")
    for key, label in (
        ("problem", "Problem"),
        ("context", "Context"),
        ("goals", "Goals"),
        ("non_goals", "Non-Goals"),
        ("proposal", "Proposal"),
        ("acceptance_criteria", "Acceptance Criteria"),
    ):
        _print_text_block(label, sections.get(key) or "Not provided.")

    decision = getattr(view, "decision")
    console.print("Decision:")
    console.print(f"  status: {decision.get('status')}")
    console.print(f"  reason: {decision.get('reason')}")
    console.print("")

    readiness = getattr(view, "readiness")
    console.print("Readiness:")
    console.print(f"  status: {readiness.status}")
    console.print(f"  score: {readiness.computed_score if readiness.computed_score is not None else 'not_assessed'}")
    console.print(f"  label: {readiness.computed_label or 'not_assessed'}")
    console.print(f"  confidence: {readiness.confidence or 'unknown'}")
    if readiness.failed_gates:
        console.print(f"  failed_gates: {', '.join(readiness.failed_gates)}")
    if readiness.missing:
        console.print(f"  missing: {', '.join(readiness.missing)}")
    console.print("")

    _print_contributions(getattr(view, "contributions").contributions)
    _print_narrative_artifacts(getattr(view, "narrative_artifacts"))
    _print_artifact_status(getattr(view, "artifact_status"))
    _print_grouped_questions(getattr(view, "questions"))
    _print_next_actions(getattr(view, "next_actions"))


def _print_text_block(label: str, text: str) -> None:
    console.print(f"  {label}:")
    for line in text.splitlines() or [""]:
        console.print(f"    {line}")
    console.print("")


def _print_contributions(contributions: list[object]) -> None:
    console.print("Structured Contributions:")
    if not contributions:
        console.print("  none")
        console.print("")
        return
    for contribution in contributions:
        console.print(
            f"  {contribution.contribution_id}  {contribution.contribution_type}  "
            f"{contribution.author or 'unknown'}"
        )
        console.print(f"    {_clip_cli(contribution.text)}")
    console.print("")


def _print_narrative_artifacts(items: list[object]) -> None:
    console.print("Narrative And Imported Artifacts:")
    if not items:
        console.print("  none")
        console.print("")
        return
    for item in items:
        console.print(f"  {item.label}: {item.status}")
        console.print(f"    source: {item.path or item.source_hint} (evidence)")
        console.print(f"    materialization: {item.materialization_kind}  provenance: {item.provenance_confidence}")
        if item.summary:
            console.print(f"    summary: {_clip_cli(item.summary)}")
    console.print("")


def _print_artifact_status(items: list[object]) -> None:
    console.print("Artifact Status:")
    for item in items:
        console.print(f"  {item.key}: {item.status}  expectation: {item.expectation}")
        console.print(f"    source: {item.path or item.source_hint} (evidence)")
        console.print(f"    materialization: {item.materialization_kind}  provenance: {item.provenance_confidence}")
        if item.next_action:
            console.print(f"    next: {item.next_action}")
    console.print("")


def _print_grouped_questions(questions: object) -> None:
    console.print("Grouped Questions:")
    console.print("  Structured owner questions:")
    if questions.owner_questions:
        for question in questions.owner_questions:
            console.print(f"    {question.question_id}  {question.priority}  {question.state}")
            console.print(f"      {question.question}")
    else:
        console.print("    none")

    console.print("  Analytical open-question contributions:")
    if questions.analytical_open_questions:
        for contribution in questions.analytical_open_questions:
            console.print(f"    {contribution.contribution_id}  {contribution.author or 'unknown'}")
            console.print(f"      {_clip_cli(contribution.text)}")
    else:
        console.print("    none")

    console.print("  Narrative question evidence:")
    if questions.narrative_question_artifacts:
        for item in questions.narrative_question_artifacts:
            console.print(f"    {item.path or item.source_hint} (evidence)")
            if item.summary:
                console.print(f"      {_clip_cli(item.summary)}")
    else:
        console.print("    none")
    console.print("")


def _print_next_actions(actions: list[str]) -> None:
    console.print("Next Actions:")
    if not actions:
        console.print("  none")
        return
    for action in actions:
        console.print(f"  {action}")


def _clip_cli(text: str, limit: int = 240) -> str:
    stripped = " ".join(str(text or "").split())
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3].rstrip() + "..."


def _wants_json(output_format: str) -> bool:
    normalized = output_format.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized == "json"


def _fail_proposal_operation(exc: ValueError, *, output_format: str) -> None:
    if _wants_json(output_format):
        message = str(exc)
        contract_failure(
            message,
            code=_proposal_error_code(message),
        )
    fail(str(exc))


def _validate_operation_key_mode(
    operation_key: str,
    *,
    json_output: bool,
    operation: str,
) -> None:
    if json_output and not operation_key.strip():
        contract_failure(
            "P2P_IDEMPOTENCY_KEY_REQUIRED: JSON proposal mutations require --operation-key",
            code="P2P_IDEMPOTENCY_KEY_REQUIRED",
        )
    if operation_key.strip() and not json_output:
        fail(
            f"P2P_{operation.upper()}_OPERATION_KEY_REQUIRES_JSON: "
            "--operation-key requires --format json"
        )


def _proposal_error_code(message: str) -> str:
    prefix = message.split(":", 1)[0]
    if prefix.startswith("P2P_"):
        return prefix
    if message.startswith("Proposal not found:") or message == "No .p2p/proposals directory found.":
        return "P2P_PROPOSAL_NOT_FOUND"
    if message.startswith("Ambiguous proposal ID:"):
        return "P2P_PROPOSAL_AMBIGUOUS_ID"
    return "P2P_PROPOSAL_OPERATION_FAILED"
