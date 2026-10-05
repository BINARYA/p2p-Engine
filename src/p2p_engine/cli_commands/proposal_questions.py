from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_commands.question_contracts import emit_question_mutation, keyed_question_mode
from p2p_engine.cli_contract import contract_failure, print_json
from p2p_engine.cli_shared import console, fail
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
        output_format: str = typer.Option("text", "--format"),
        limit: int = typer.Option(20, "--limit", min=1, max=100),
        offset: int = typer.Option(0, "--offset", min=0),
        state: str = typer.Option("", "--state"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show proposal question state status."""
        if _question_page(root, proposal_id, output_format, limit, offset, state):
            return
        try:
            view = workspace_for(root).read_proposal_questions(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_question_state(view)

    @proposal_questions_app.command("list")
    def questions_list(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        output_format: str = typer.Option("text", "--format"),
        limit: int = typer.Option(20, "--limit", min=1, max=100),
        offset: int = typer.Option(0, "--offset", min=0),
        state: str = typer.Option("", "--state"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """List proposal questions."""
        if _question_page(root, proposal_id, output_format, limit, offset, state):
            return
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
        expected_revision: int | None = typer.Option(None, "--expected-revision", min=1),
        output_format: str = typer.Option("text", "--format"),
        operation_key: str = typer.Option("", "--operation-key"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record an answer for a proposal question."""
        if _question_write(root=root, leaf="answer", proposal_id=proposal_id, actor=actor,
            output_format=output_format, operation_key=operation_key, executor=executor,
            executor_kind=executor_kind, authority_context=authority_context,
            question_id=question_id, expected_revision=expected_revision, answer=answer,
            source=source, replace_answer=replace):
            return
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
        expected_revision: int | None = typer.Option(None, "--expected-revision", min=1),
        output_format: str = typer.Option("text", "--format"),
        operation_key: str = typer.Option("", "--operation-key"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Defer a proposal question."""
        if _question_write(root=root, leaf="defer", proposal_id=proposal_id, actor=actor,
            output_format=output_format, operation_key=operation_key, executor=executor,
            executor_kind=executor_kind, authority_context=authority_context,
            question_id=question_id, expected_revision=expected_revision, reason=reason):
            return
        _set_question_state(proposal_id, question_id, ProposalQuestionState.defer, reason=reason, actor=actor, root=root)

    @proposal_questions_app.command("mute")
    def questions_mute(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        reason: str = typer.Option("", "--reason", help="Reason for muting"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        expected_revision: int | None = typer.Option(None, "--expected-revision", min=1),
        output_format: str = typer.Option("text", "--format"),
        operation_key: str = typer.Option("", "--operation-key"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Mute a proposal question."""
        if _question_write(root=root, leaf="mute", proposal_id=proposal_id, actor=actor,
            output_format=output_format, operation_key=operation_key, executor=executor,
            executor_kind=executor_kind, authority_context=authority_context,
            question_id=question_id, expected_revision=expected_revision, reason=reason):
            return
        _set_question_state(proposal_id, question_id, ProposalQuestionState.muted, reason=reason, actor=actor, root=root)

    @proposal_questions_app.command("reopen")
    def questions_reopen(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        question_id: str = typer.Argument(..., help="Question ID, e.g. Q001"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        expected_revision: int | None = typer.Option(None, "--expected-revision", min=1),
        output_format: str = typer.Option("text", "--format"),
        operation_key: str = typer.Option("", "--operation-key"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Reopen a proposal question."""
        if _question_write(root=root, leaf="reopen", proposal_id=proposal_id, actor=actor,
            output_format=output_format, operation_key=operation_key, executor=executor,
            executor_kind=executor_kind, authority_context=authority_context,
            question_id=question_id, expected_revision=expected_revision):
            return
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
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show the next eligible proposal question."""
        if output_format == "json":
            try:
                print_json(workspace_for(root).question_contract_service().next(scope="proposal", proposal_id=proposal_id,
                    include_muted=include_muted, include_deferred=include_deferred))
            except ValueError as exc:
                contract_failure(str(exc))
            return
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
        question_ids: list[str] | None = typer.Option(None, "--question"),
        output_format: str = typer.Option("text", "--format"),
        operation_key: str = typer.Option("", "--operation-key"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Mark answered questions as applied and print an apply summary."""
        if _question_write(root=root, leaf="apply", proposal_id=proposal_id, actor=actor,
            output_format=output_format, operation_key=operation_key, executor=executor,
            executor_kind=executor_kind, authority_context=authority_context,
            question_ids=question_ids or ()):
            return
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


def _question_page(root: Path, proposal_id: str, output_format: str, limit: int, offset: int, state: str) -> bool:
    if output_format == "text":
        return False
    if output_format != "json":
        contract_failure("P2P_FORMAT_INVALID: --format must be text or json")
    try:
        print_json(workspace_for(root).question_contract_service().page(scope="proposal", proposal_id=proposal_id,
            limit=limit, offset=offset, state=state))
    except ValueError as exc:
        contract_failure(str(exc))
    return True


def _question_write(*, root: Path, leaf: str, proposal_id: str, actor: str,
    output_format: str, operation_key: str, executor: str, executor_kind: str,
    authority_context: Path | None, **request: object) -> bool:
    keyed = keyed_question_mode(output_format=output_format, operation_key=operation_key,
        authority_context=authority_context, executor=executor, root=root, executor_kind=executor_kind)
    if output_format == "json" and not keyed:
        contract_failure("P2P_IDEMPOTENCY_KEY_REQUIRED: new proposal JSON mutations require --operation-key")
    if not keyed:
        if output_format != "text":
            contract_failure("P2P_FORMAT_INVALID: --format must be text or json")
        return False
    emit_question_mutation(root=root, scope="proposal", leaf=leaf, proposal_id=proposal_id,
        actor=actor, operation_key=operation_key, executor=executor, executor_kind=executor_kind,
        authority_context=authority_context, **request)
    return True


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
