from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import typer

from p2p_engine.cli_contract import contract_failure, print_json
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
        operation_key: str = typer.Option("", "--operation-key"),
        actor: str = typer.Option("", "--actor", help="Actor recording the operation; defaults to author"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Append a contribution to a proposal."""
        _add_contribution_command(
            proposal_id=proposal_id,
            text=text,
            contribution_type=contribution_type,
            relevance=relevance,
            author=author,
            operation_key=operation_key,
            actor=actor,
            root=root,
            output_format=output_format,
        )

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
        operation_key: str = typer.Option("", "--operation-key"),
        actor: str = typer.Option("", "--actor", help="Actor recording the operation; defaults to author"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Append a contribution to a proposal."""
        _add_contribution_command(
            proposal_id=proposal_id,
            text=text,
            contribution_type=contribution_type,
            relevance=relevance,
            author=author,
            operation_key=operation_key,
            actor=actor,
            root=root,
            output_format=output_format,
        )

    @contribution_app.command("list")
    def contribution_list(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        contribution_type: str | None = typer.Option(None, "--type", help=CONTRIBUTION_TYPE_HELP),
        limit: int = typer.Option(50, "--limit", min=1, max=100),
        offset: int = typer.Option(0, "--offset", min=0),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List contributions for a proposal."""
        _list_contributions_command(
            proposal_id=proposal_id,
            contribution_type=contribution_type,
            limit=limit,
            offset=offset,
            root=root,
            output_format=output_format,
        )

    @proposal_contribution_app.command("list")
    def proposal_contribution_list(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        contribution_type: str | None = typer.Option(None, "--type", help=CONTRIBUTION_TYPE_HELP),
        limit: int = typer.Option(50, "--limit", min=1, max=100),
        offset: int = typer.Option(0, "--offset", min=0),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List contributions for a proposal."""
        _list_contributions_command(
            proposal_id=proposal_id,
            contribution_type=contribution_type,
            limit=limit,
            offset=offset,
            root=root,
            output_format=output_format,
        )

    @proposal_app.command("contributions")
    def proposal_contributions(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        contribution_type: str | None = typer.Option(None, "--type", help=CONTRIBUTION_TYPE_HELP),
        limit: int = typer.Option(50, "--limit", min=1, max=100),
        offset: int = typer.Option(0, "--offset", min=0),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List contributions for a proposal."""
        _list_contributions_command(
            proposal_id=proposal_id,
            contribution_type=contribution_type,
            limit=limit,
            offset=offset,
            root=root,
            output_format=output_format,
        )


def _add_contribution_command(
    *,
    proposal_id: str,
    text: str,
    contribution_type: str,
    relevance: str,
    author: str,
    operation_key: str,
    actor: str,
    root: Path,
    output_format: str,
) -> None:
    json_output = _wants_json(output_format)
    _validate_operation_key_mode(operation_key, json_output=json_output)
    workspace = workspace_for(root)
    try:
        parsed_type = parse_contribution_type(contribution_type)
        if json_output:
            print_json(
                workspace.add_contribution_with_operation_key(
                    proposal_id=proposal_id,
                    contribution_type=parsed_type,
                    text=text,
                    relevance_hint=relevance,
                    author=author,
                    operation_key=operation_key,
                    actor=actor,
                )
            )
            return
        contribution = workspace.add_contribution(
            proposal_id=proposal_id,
            contribution_type=parsed_type,
            text=text,
            relevance_hint=relevance,
            author=author,
        )
    except ValueError as exc:
        _fail_contribution_operation(exc, output_format=output_format)
    console.print("[green]Contribution added.[/green]")
    console.print(f"  id: {contribution.contribution_id}")
    console.print(f"  proposal: {proposal_id}")


def _list_contributions_command(
    *,
    proposal_id: str,
    contribution_type: str | None,
    limit: int,
    offset: int,
    root: Path,
    output_format: str,
) -> None:
    try:
        parsed_type = (
            parse_contribution_type(contribution_type)
            if contribution_type is not None
            else None
        )
        if _wants_json(output_format):
            print_json(
                {
                    "proposal_contribution_list": workspace_for(
                        root
                    ).proposal_contribution_list_contract(
                        proposal_id,
                        contribution_type=parsed_type,
                        limit=limit,
                        offset=offset,
                    )
                }
            )
            return
        contributions = workspace_for(root).list_contributions(proposal_id)
        if parsed_type is not None:
            contributions = replace(
                contributions,
                contributions=[
                    contribution
                    for contribution in contributions.contributions
                    if contribution.contribution_type == parsed_type
                ],
            )
    except ValueError as exc:
        _fail_contribution_operation(exc, output_format=output_format)
    _print_contribution_list(contributions)


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


def _wants_json(output_format: str) -> bool:
    normalized = output_format.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized == "json"


def _validate_operation_key_mode(operation_key: str, *, json_output: bool) -> None:
    if json_output and not operation_key.strip():
        contract_failure(
            "P2P_IDEMPOTENCY_KEY_REQUIRED: JSON contribution mutations require --operation-key",
            code="P2P_IDEMPOTENCY_KEY_REQUIRED",
        )
    if operation_key.strip() and not json_output:
        fail(
            "P2P_PROPOSAL_CONTRIBUTION_OPERATION_KEY_REQUIRES_JSON: "
            "--operation-key requires --format json"
        )


def _fail_contribution_operation(exc: ValueError, *, output_format: str) -> None:
    if _wants_json(output_format):
        message = str(exc)
        contract_failure(message, code=_contribution_error_code(message))
    fail(str(exc))


def _contribution_error_code(message: str) -> str:
    prefix = message.split(":", 1)[0]
    if prefix.startswith("P2P_"):
        return prefix
    if message.startswith("Invalid contribution type:"):
        return "P2P_CONTRIBUTION_INVALID_TYPE"
    if message.startswith("Proposal not found:") or message == "No .p2p/proposals directory found.":
        return "P2P_PROPOSAL_NOT_FOUND"
    if message.startswith("Ambiguous proposal ID:"):
        return "P2P_PROPOSAL_AMBIGUOUS_ID"
    return "P2P_CONTRIBUTION_OPERATION_FAILED"
