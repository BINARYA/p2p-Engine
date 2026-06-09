from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.proposal_questions import ProposalQuestionPriority, ProposalQuestionState


def register_proposal_question_commands(proposal_questions_app: typer.Typer) -> None:
    @proposal_questions_app.command("init")
    def questions_init(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Initialize proposal question state."""
        try:
            view = workspace_for(root).initialize_proposal_questions(proposal_id, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal question state initialized.[/green]")
        print_question_state(view)

    @proposal_questions_app.command("status")
    def questions_status(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show proposal question state status."""
        try:
            view = workspace_for(root).read_proposal_questions(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_question_state(view)

    @proposal_questions_app.command("list")
    def questions_list(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List proposal questions."""
        try:
            view = workspace_for(root).read_proposal_questions(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_question_state(view, include_questions=True)

    @proposal_questions_app.command("add")
    def questions_add(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        gap: str = typer.Option(..., "--gap", help="Readiness gap or criterion"),
        question: str = typer.Option(..., "--question", help="Question text"),
        priority: ProposalQuestionPriority = typer.Option(ProposalQuestionPriority.medium, "--priority", help="Question priority"),
        rationale: str = typer.Option("", "--rationale", help="Why this question matters"),
        group_id: str = typer.Option("", "--group-id", help="Existing group ID"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Add a proposal question."""
        try:
            result = workspace_for(root).add_proposal_question(
                proposal_id,
                gap=gap,
                question=question,
                priority=priority,
                rationale=rationale,
                group_id=group_id,
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Question added.[/green]")
        if result.question:
            print_question(result.question)

    @proposal_questions_app.command("answer")
    def questions_answer(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        answer: str = typer.Argument(..., help="Answer text"),
        source: str = typer.Option("owner", "--source", help="Answer source"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        replace: bool = typer.Option(False, "--replace", help="Replace an existing answer"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record an answer for a proposal question."""
        try:
            result = workspace_for(root).answer_proposal_question(
                proposal_id,
                question_id,
                answer,
                source=source,
                actor=actor,
                replace=replace,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Question answered.[/green]")
        if result.question:
            print_question(result.question)

    @proposal_questions_app.command("defer")
    def questions_defer(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        reason: str = typer.Option("", "--reason", help="Reason for deferring"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Defer a proposal question."""
        _set_question_state(proposal_id, question_id, ProposalQuestionState.defer, reason=reason, actor=actor, root=root)

    @proposal_questions_app.command("mute")
    def questions_mute(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        reason: str = typer.Option("", "--reason", help="Reason for muting"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Mute a proposal question."""
        _set_question_state(proposal_id, question_id, ProposalQuestionState.muted, reason=reason, actor=actor, root=root)

    @proposal_questions_app.command("reopen")
    def questions_reopen(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Reopen a proposal question."""
        _set_question_state(proposal_id, question_id, ProposalQuestionState.to_answer, actor=actor, root=root)

    @proposal_questions_app.command("retire")
    def questions_retire(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        reason: str = typer.Option("", "--reason", help="Reason for retiring"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Retire a proposal question."""
        _set_question_state(proposal_id, question_id, ProposalQuestionState.retired, reason=reason, actor=actor, root=root)

    @proposal_questions_app.command("supersede")
    def questions_supersede(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        superseded_by: str = typer.Argument(..., help="Replacement question ID, e.g. Q002"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Mark a proposal question as superseded by another question."""
        try:
            result = workspace_for(root).supersede_proposal_question(
                proposal_id,
                question_id,
                superseded_by,
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Question superseded.[/green]")
        if result.question:
            print_question(result.question)

    @proposal_questions_app.command("group-status")
    def questions_group_status(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        group_id: str = typer.Argument(..., help="Question group ID, e.g. QG001"),
        state: ProposalQuestionState = typer.Option(..., "--state", help="Group re-ask state"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Set proposal question group re-ask state."""
        try:
            view = workspace_for(root).set_proposal_question_group_state(proposal_id, group_id, state, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Question group state updated.[/green]")
        print_question_state(view)

    @proposal_questions_app.command("next")
    def questions_next(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        include_muted: bool = typer.Option(False, "--include-muted", help="Include muted questions"),
        include_deferred: bool = typer.Option(False, "--include-deferred", help="Include deferred question groups"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show the next eligible proposal question."""
        try:
            question = workspace_for(root).next_proposal_question(
                proposal_id,
                include_muted=include_muted,
                include_deferred=include_deferred,
            )
        except ValueError as exc:
            fail(str(exc))
        if question is None:
            console.print("No eligible proposal question.")
            return
        print_question(question)

    @proposal_questions_app.command("reassess")
    def questions_reassess(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Reassess proposal question state."""
        try:
            view = workspace_for(root).reassess_proposal_questions(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_question_state(view, include_questions=True)

    @proposal_questions_app.command("apply")
    def questions_apply(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Mark answered questions as applied and print an apply summary."""
        try:
            summary = workspace_for(root).apply_proposal_question_answers(proposal_id, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        console.print(summary.summary)

    @proposal_questions_app.command("import")
    def questions_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        source: Path = typer.Argument(..., help="YAML question state file"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import proposal question state."""
        try:
            view = workspace_for(root).import_proposal_questions(proposal_id, source, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal question state imported.[/green]")
        print_question_state(view)


def _set_question_state(
    proposal_id: str,
    question_id: str,
    state: ProposalQuestionState,
    *,
    reason: str = "",
    actor: str,
    root: Path,
) -> None:
    try:
        result = workspace_for(root).set_proposal_question_state(proposal_id, question_id, state, reason=reason, actor=actor)
    except ValueError as exc:
        fail(str(exc))
    console.print(f"[green]Question state set to {state.value}.[/green]")
    if result.question:
        print_question(result.question)


def print_question_state(view: object, *, include_questions: bool = False) -> None:
    console.print(f"Proposal questions for [bold]{getattr(view, 'proposal_id')}[/bold]")
    console.print(f"  status: {getattr(view, 'status')}")
    console.print(f"  path: {getattr(view, 'path')}")
    console.print(f"  schema_version: {getattr(view, 'schema_version') or 'none'}")
    console.print(f"  groups: {len(getattr(view, 'groups'))}")
    console.print(f"  questions: {len(getattr(view, 'questions'))}")
    if getattr(view, "status") == "not_initialized":
        console.print(f"  suggested_next: p2p proposal questions init {getattr(view, 'proposal_id')}")
    if include_questions:
        questions = getattr(view, "questions")
        if not questions:
            console.print("  question_list: none")
        for question in questions:
            print_question(question, indent="  ")


def print_question(question: object, *, indent: str = "") -> None:
    console.print(f"{indent}{getattr(question, 'question_id')}  {getattr(question, 'state').value}  {getattr(question, 'priority').value}")
    console.print(f"{indent}  group: {getattr(question, 'group_id') or 'none'}")
    console.print(f"{indent}  gap: {getattr(question, 'gap')}")
    console.print(f"{indent}  question: {getattr(question, 'question')}")
    answer = getattr(question, "answer")
    console.print(f"{indent}  answer: {answer if answer else ''}")
    if getattr(question, "deferred_reason"):
        console.print(f"{indent}  deferred_reason: {getattr(question, 'deferred_reason')}")
    if getattr(question, "muted_reason"):
        console.print(f"{indent}  muted_reason: {getattr(question, 'muted_reason')}")
