from __future__ import annotations

import uuid
from pathlib import Path

import typer

from p2p_engine.cli_commands.formatting import emit_structured
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.services.authority import AuthorityContractCodec


def register_choice_commands(choice_app: typer.Typer) -> None:
    @choice_app.command("create")
    def choice_create(
        title: str = typer.Option(..., "--title", help="Choice title"),
        problem: str = typer.Option(..., "--problem", help="Stable problem statement"),
        context: str = typer.Option(..., "--context", help="Stable decision context"),
        governance_boundary: str = typer.Option(
            "This choice is advisory until decided through P2P governance.",
            "--governance-boundary",
            help="Stable governance boundary",
        ),
        option: list[str] = typer.Option(..., "--option", help="Choice option. Can be repeated."),
        related: list[str] | None = typer.Option(None, "--related", help="Related proposal ID. Can be repeated."),
        source: str | None = typer.Option(None, "--source", help="Source artifact, e.g. INTAKE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create a project choice with multiple options."""
        try:
            choice = workspace_for(root).create_choice(
                title=title,
                options=option,
                related=related,
                source=source,
                problem=problem,
                context=context,
                governance_boundary=governance_boundary,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Choice created.[/green]")
        console.print(f"  id: {choice.choice_id}")
        console.print(f"  status: {choice.status}")
        console.print(f"  path: {choice.path}")

    @choice_app.command("list")
    def choice_list(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List project choices."""
        try:
            choices = workspace_for(root).choice_statuses()
        except ValueError as exc:
            fail(str(exc))
        console.print("Choices")
        if not choices:
            console.print("  none")
            return
        for choice in choices:
            selected = f" -> {choice.selected_option}" if choice.selected_option else ""
            console.print(f"  {choice.choice_id}  {choice.status}  {choice.title}{selected}")

    @choice_app.command("status")
    def choice_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List project choices and proposal-local choice candidates."""
        workspace = workspace_for(root)
        try:
            choices = workspace.choice_statuses()
            findings = workspace.discover_choices()
        except ValueError as exc:
            fail(str(exc))
        console.print("Choice status")
        console.print("  project choices:")
        if choices:
            for choice in choices:
                selected = f" -> {choice.selected_option}" if choice.selected_option else ""
                console.print(f"    {choice.choice_id}  {choice.status}  {choice.title}{selected}")
        else:
            console.print("    none")
        candidates = [finding for finding in findings if finding.kind == "proposal_local_choice_candidate"]
        console.print("  proposal-local candidates:")
        if candidates:
            for finding in candidates:
                console.print(f"    {finding.target}  {finding.severity}  {finding.reason}")
        else:
            console.print("    none")

    @choice_app.command("show")
    def choice_show(
        choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show project choice details."""
        try:
            choice = workspace_for(root).show_choice(choice_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"{choice.choice_id} - [bold]{choice.title}[/bold]")
        console.print(f"  status: {choice.status}")
        console.print(f"  path: {choice.path}")
        console.print(f"  selected: {choice.selected_option or 'none'}")
        console.print(f"  terminal: {choice.terminal}")
        console.print(f"  seal: {choice.seal_status}")
        console.print(f"  integrity: {choice.integrity_status}")
        if choice.replacement_choice_id:
            console.print(f"  replacement: {choice.replacement_choice_id}")
        if choice.supersedes:
            console.print(f"  supersedes: {', '.join(choice.supersedes)}")
        console.print("  options:")
        if choice.options:
            for option in choice.options:
                console.print(f"    {option.get('id', '-')}: {option.get('title', '')}")
        else:
            console.print("    none")
        console.print("  blocks:")
        active_blocks = [
            block
            for block in choice.blocks
            if isinstance(block, dict) and block.get("status", "active") == "active"
        ]
        if active_blocks:
            for block in active_blocks:
                console.print(
                    f"    {block.get('target_type', 'target')} {block.get('target', '-')}  "
                    f"{block.get('status', 'active')}  {block.get('reason', '')}"
                )
        else:
            console.print("    none")

    @choice_app.command("discover")
    def choice_discover(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Discover advisory choice findings without modifying state."""
        try:
            findings = workspace_for(root).discover_choices()
        except ValueError as exc:
            fail(str(exc))
        console.print("Choice discovery")
        if not findings:
            console.print("  none")
            return
        for finding in findings:
            console.print(f"  {finding.finding_id}  {finding.severity}  {finding.kind}  {finding.target}")
            console.print(f"    reason: {finding.reason}")
            console.print(f"    command: {finding.suggested_command}")

    @choice_app.command("governance-preflight")
    def choice_governance_preflight(
        choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
        option: str = typer.Option(..., "--option", help="Option ID or title to evaluate"),
        actor: str = typer.Option(..., "--actor", help="Actor requesting governance readiness"),
        precedent_id: str | None = typer.Option(None, "--precedent", help="Explicit precedent ID"),
        tag: str | None = typer.Option(None, "--tag", help="Explicit precedent tag"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text, json, or yaml"),
    ) -> None:
        """Preview governance readiness for a choice without deciding it."""
        try:
            result = workspace_for(root).choice_governance_preflight(
                choice_id,
                option=option,
                actor=actor,
                precedent_id=precedent_id,
                tag=tag,
            )
        except ValueError as exc:
            fail(str(exc))
        if emit_structured(result, output_format):
            if result.result.status == "blocked":
                raise typer.Exit(1)
            return
        console.print(f"Governance preflight for [bold]{result.target.id}[/bold]")
        console.print(f"  status: {result.result.status}")
        console.print(f"  actor: {result.actor.id} ({result.actor.role})")
        console.print(f"  option: {result.selection.resolved_option or result.selection.requested_option}")
        console.print(f"  vote alignment: {result.vote_summary.alignment}")
        if result.blocking_errors:
            console.print("  blocking errors:")
            for error in result.blocking_errors:
                console.print(f"    {error.code}: {error.message}")
        if result.warnings:
            console.print("  warnings:")
            for warning in result.warnings:
                console.print(f"    {warning.code}: {warning.message}")
        if result.precedents:
            console.print("  precedents:")
            for match in result.precedents:
                console.print(f"    {match.precedent_id}: {match.match_reason} {match.related_target}")
        if result.result.status == "blocked":
            raise typer.Exit(1)

    @choice_app.command("block")
    def choice_block(
        choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
        change: str | None = typer.Option(None, "--change", help="Change Set blocked by this choice"),
        proposal: str | None = typer.Option(None, "--proposal", help="Proposal blocked by this choice"),
        reason: str = typer.Option(..., "--reason", help="Why the choice blocks the target"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record an explicit active choice blocker."""
        if bool(change) == bool(proposal):
            fail("Provide exactly one of --change or --proposal.")
        target = change or proposal or ""
        target_type = "change" if change else "proposal"
        try:
            choice = workspace_for(root).block_choice(choice_id, target, target_type, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Choice blocker recorded.[/green]")
        console.print(f"  choice: {choice.choice_id}")
        console.print(f"  {target_type}: {target}")

    @choice_app.command("unblock")
    def choice_unblock(
        choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
        change: str | None = typer.Option(None, "--change", help="Change Set to unblock"),
        proposal: str | None = typer.Option(None, "--proposal", help="Proposal to unblock"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Deactivate an explicit choice blocker."""
        if bool(change) == bool(proposal):
            fail("Provide exactly one of --change or --proposal.")
        target = change or proposal or ""
        target_type = "change" if change else "proposal"
        try:
            choice = workspace_for(root).unblock_choice(choice_id, target, target_type)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Choice blocker cleared.[/green]")
        console.print(f"  choice: {choice.choice_id}")
        console.print(f"  {target_type}: {target}")

    @choice_app.command("decide")
    def choice_decide(
        choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
        option: str = typer.Option(..., "--option", help="Option ID or title to select"),
        reason: str = typer.Option(..., "--reason", help="Decision rationale"),
        decider: str = typer.Option("owner", "--decider", help="Decision owner"),
        operation_key: str = typer.Option("", "--operation-key", help="Idempotency key"),
        preview_token: str = typer.Option("", "--preview-token", help="Exact reviewed preview token"),
        confirm: bool = typer.Option(False, "--confirm", help="Apply the reviewed transition"),
        output_format: str = typer.Option("text", "--format", help="text, json, or yaml"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview or apply an immutable Choice decision."""
        _choice_transition(
            root=root,
            choice_id=choice_id,
            transition="decide",
            reason=reason,
            actor=decider,
            operation_key=operation_key,
            preview_token=preview_token,
            confirm=confirm,
            option=option,
            output_format=output_format,
        )

    @choice_app.command("withdraw")
    def choice_withdraw(
        choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
        reason: str = typer.Option(..., "--reason"),
        actor: str = typer.Option("owner", "--actor"),
        operation_key: str = typer.Option("", "--operation-key"),
        preview_token: str = typer.Option("", "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text, json, or yaml"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """Preview or apply terminal withdrawal without selecting an option."""
        _choice_transition(
            root=root,
            choice_id=choice_id,
            transition="withdraw",
            reason=reason,
            actor=actor,
            operation_key=operation_key,
            preview_token=preview_token,
            confirm=confirm,
            output_format=output_format,
        )

    @choice_app.command("supersede")
    def choice_supersede(
        choice_id: str = typer.Argument(..., help="Historical Choice ID"),
        replacement: str = typer.Option(..., "--replacement", help="Existing open sealed replacement Choice"),
        reason: str = typer.Option(..., "--reason"),
        actor: str = typer.Option("owner", "--actor"),
        operation_key: str = typer.Option("", "--operation-key"),
        preview_token: str = typer.Option("", "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text, json, or yaml"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """Preview or apply terminal supersession with typed lineage."""
        _choice_transition(
            root=root,
            choice_id=choice_id,
            transition="supersede",
            reason=reason,
            actor=actor,
            operation_key=operation_key,
            preview_token=preview_token,
            confirm=confirm,
            replacement_choice_id=replacement,
            output_format=output_format,
        )

    @choice_app.command("transition-preview")
    def choice_transition_preview(
        choice_id: str = typer.Argument(...),
        transition: str = typer.Option(..., "--transition", help="decide, withdraw, or supersede"),
        reason: str = typer.Option(..., "--reason"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        operation_key: str = typer.Option(..., "--operation-key"),
        option: str | None = typer.Option(None, "--option"),
        replacement: str | None = typer.Option(None, "--replacement"),
        effective_on: str | None = typer.Option(None, "--effective-on"),
        override_blockers: bool = typer.Option(False, "--override-blockers"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        output_format: str = typer.Option("text", "--format", help="text, json, or yaml"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        context = _authority_context(authority_context)
        try:
            plan = workspace_for(root).preview_choice_transition(
                choice_id,
                transition=transition,
                reason=reason,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                operation_key=operation_key,
                option=option,
                replacement_choice_id=replacement,
                effective_on=effective_on,
                blocker_override=override_blockers,
                authority_context=context,
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        _print_transition(plan, output_format, preview=True)

    @choice_app.command("transition-apply")
    def choice_transition_apply(
        choice_id: str = typer.Argument(...),
        transition: str = typer.Option(..., "--transition", help="decide, withdraw, or supersede"),
        reason: str = typer.Option(..., "--reason"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        operation_key: str = typer.Option(..., "--operation-key"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        option: str | None = typer.Option(None, "--option"),
        replacement: str | None = typer.Option(None, "--replacement"),
        effective_on: str | None = typer.Option(None, "--effective-on"),
        override_blockers: bool = typer.Option(False, "--override-blockers"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        output_format: str = typer.Option("text", "--format", help="text, json, or yaml"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        context = _authority_context(authority_context)
        try:
            result = workspace_for(root).apply_choice_transition(
                choice_id,
                transition=transition,
                reason=reason,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                operation_key=operation_key,
                option=option,
                replacement_choice_id=replacement,
                effective_on=effective_on,
                blocker_override=override_blockers,
                authority_context=context,
                channel="cli",
                preview_token=preview_token,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_transition(result, output_format, preview=False)


def _choice_transition(
    *,
    root: Path,
    choice_id: str,
    transition: str,
    reason: str,
    actor: str,
    operation_key: str,
    preview_token: str,
    confirm: bool,
    output_format: str,
    option: str | None = None,
    replacement_choice_id: str | None = None,
) -> None:
    key = operation_key.strip() or f"local-choice:{uuid.uuid4()}"
    workspace = workspace_for(root)
    request = {
        "transition": transition,
        "reason": reason,
        "actor_id": actor,
        "executor_id": actor,
        "executor_kind": "person",
        "operation_key": key,
        "option": option,
        "replacement_choice_id": replacement_choice_id,
        "channel": "cli",
    }
    try:
        if preview_token:
            result = workspace.apply_choice_transition(
                choice_id, preview_token=preview_token, confirm=confirm, **request
            )
            _print_transition(result, output_format, preview=False)
            return
        plan = workspace.preview_choice_transition(choice_id, **request)
    except ValueError as exc:
        fail(str(exc))
    _print_transition(plan, output_format, preview=True, operation_key=key)


def _authority_context(path: Path | None):
    if path is None:
        return None
    try:
        return AuthorityContractCodec().context_from_path(path)
    except ValueError as exc:
        fail(str(exc))


def _print_transition(
    value: object,
    output_format: str,
    *,
    preview: bool,
    operation_key: str = "",
) -> None:
    payload = value.to_dict()  # type: ignore[attr-defined]
    if emit_structured(payload, output_format):
        return
    console.print("Choice transition preview" if preview else "[green]Choice transition applied.[/green]")
    console.print(f"  choice: {payload.get('choice_id') or payload.get('choice', {}).get('choice_id')}")
    console.print(f"  transition: {payload.get('transition')}")
    if preview:
        mutation = payload.get("mutation", {})
        console.print(f"  target state: {payload.get('target_state')}")
        console.print(f"  operation key: {operation_key or 'retain the supplied key for apply'}")
        console.print(f"  preview token: {mutation.get('preview_token')}")
        console.print("  apply with `p2p choice transition-apply ... --preview-token <token> --confirm`.")
    else:
        console.print(f"  status: {payload.get('status')}")
