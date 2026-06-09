from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactExpectation,
    ProposalArtifactRiskFlag,
    ProposalArtifactStatus,
)


def register_proposal_artifact_commands(proposal_artifact_app: typer.Typer) -> None:
    @proposal_artifact_app.command("status")
    def proposal_artifact_status(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show proposal artifact coverage state."""
        try:
            view = workspace_for(root).read_proposal_artifacts(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        print_artifact_state(view)

    @proposal_artifact_app.command("init")
    def proposal_artifact_init(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Initialize or refresh proposal artifact coverage state."""
        try:
            view = workspace_for(root).initialize_proposal_artifacts(proposal_id, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal artifact state initialized.[/green]")
        print_artifact_state(view)

    @proposal_artifact_app.command("set")
    def proposal_artifact_set(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        artifact_id: str = typer.Argument(..., help="Artifact id, e.g. impact_map"),
        expectation: ProposalArtifactExpectation | None = typer.Option(None, "--expectation", help="Artifact expectation"),
        status: ProposalArtifactStatus | None = typer.Option(None, "--status", help="Artifact lifecycle status"),
        reason: str = typer.Option("", "--reason", help="Concrete rationale for the status"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        source: str = typer.Option("agent", "--source", help="Source of the update"),
        risk_flag: list[ProposalArtifactRiskFlag] | None = typer.Option(None, "--risk-flag", help="Risk flag. Can be repeated."),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Set one proposal artifact state record."""
        try:
            operation = workspace_for(root).set_proposal_artifact_state(
                proposal_id,
                artifact_id,
                expectation=expectation,
                status=status,
                reason=reason,
                actor=actor,
                source=source,
                risk_flags=risk_flag,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print(f"[green]{operation.message}[/green]")
        if operation.artifact is not None:
            print_artifact_record(operation.artifact)

    @proposal_artifact_app.command("confirm")
    def proposal_artifact_confirm(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        artifact_id: str = typer.Argument(..., help="Artifact id, e.g. impact_map"),
        actor: str = typer.Option("owner", "--actor", help="Owner identity confirming the state"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record owner confirmation for one artifact state."""
        try:
            operation = workspace_for(root).confirm_proposal_artifact_state(proposal_id, artifact_id, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"[green]{operation.message}[/green]")
        if operation.artifact is not None:
            print_artifact_record(operation.artifact)

    @proposal_artifact_app.command("mark-legacy")
    def proposal_artifact_mark_legacy(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option("Proposal predates artifact-aware state.", "--reason", help="Legacy rationale"),
        actor: str = typer.Option("local", "--actor", help="Actor recording the operation"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record advisory legacy absence for proposal artifact state."""
        try:
            view = workspace_for(root).mark_proposal_artifacts_legacy(proposal_id, reason=reason, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Proposal artifact state marked legacy.[/green]")
        print_artifact_state(view)


def print_artifact_state(view: object) -> None:
    console.print(f"Proposal artifact state for [bold]{getattr(view, 'proposal_id')}[/bold]")
    console.print(f"  status: {getattr(view, 'status')}")
    console.print(f"  path: {getattr(view, 'path')}")
    schema_version = getattr(view, "schema_version")
    console.print(f"  schema_version: {schema_version if schema_version is not None else 'none'}")
    legacy_state = getattr(view, "legacy_state")
    if legacy_state:
        console.print(f"  legacy_state: {legacy_state.value}")
        console.print(f"  legacy_reason: {getattr(view, 'legacy_reason')}")
    console.print("  artifacts:")
    artifacts = getattr(view, "artifacts")
    if not artifacts:
        console.print("    none")
    for artifact in artifacts:
        print_artifact_record(artifact, indent="    ")
    console.print("  suggested_next:")
    suggested_next = getattr(view, "suggested_next")
    if suggested_next:
        for command in suggested_next:
            console.print(f"    - {command}")
    else:
        console.print("    none")


def print_artifact_record(record: object, *, indent: str = "  ") -> None:
    risk_flags = ", ".join(flag.value for flag in getattr(record, "risk_flags"))
    console.print(
        f"{indent}{getattr(record, 'artifact_id')}  {getattr(record, 'expectation').value}  "
        f"{getattr(record, 'status').value}  {getattr(record, 'confirmation').value}"
    )
    console.print(f"{indent}  filename: {getattr(record, 'filename')}")
    console.print(f"{indent}  reason: {getattr(record, 'reason') or 'none'}")
    console.print(f"{indent}  actor: {getattr(record, 'actor') or 'none'}")
    console.print(f"{indent}  source: {getattr(record, 'source') or 'none'}")
    console.print(f"{indent}  risk_flags: {risk_flags or 'none'}")
