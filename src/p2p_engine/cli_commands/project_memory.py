from __future__ import annotations

from pathlib import Path
import uuid

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail, workspace as workspace_for, yaml_dump_for_cli
from p2p_engine.services.authority import AuthorityContractCodec


def register_project_memory_commands(
    proposal_scope_app: typer.Typer,
    project_memory_app: typer.Typer,
) -> None:
    @project_memory_app.callback()
    def project_memory_group() -> None:
        """Inspect project-memory organization against the current structure."""

    @proposal_scope_app.command("show")
    def scope_show(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            scope = workspace_for(root).proposal_memory_scope(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "proposal.scope.show",
            {"project_memory_scope": scope.to_dict()},
            normalized,
        )

    @proposal_scope_app.command("set")
    def scope_set(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        kind: str = typer.Option(..., "--kind", help="sections, project_global or unassigned"),
        section_id: list[str] | None = typer.Option(None, "--section-id", help="Active section ID; repeat for multiple sections"),
        expected_memory_revision: str = typer.Option(..., "--expected-memory-revision", help="Current opaque project-memory revision"),
        expected_structure_revision: int = typer.Option(..., "--expected-structure-revision", min=1),
        actor: str = typer.Option("owner", "--actor", help="Authorized project subject"),
        executor: str = typer.Option("", "--executor", help="Executing identity; defaults to actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        operation_key: str = typer.Option("", "--operation-key", help="Opaque idempotency key; required for JSON"),
        authority_context: Path | None = typer.Option(None, "--authority-context", help="External AuthorityContext JSON; JSON mode only"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        normalized = _output_format(output_format)
        if normalized == "json" and not operation_key.strip():
            fail("P2P_IDEMPOTENCY_KEY_REQUIRED: JSON scope mutation requires --operation-key")
        if normalized != "json" and authority_context is not None:
            fail("P2P_AUTHORITY_CONTEXT_INVALID: --authority-context requires --format json")
        context = None
        if authority_context is not None:
            try:
                context = AuthorityContractCodec().context_from_path(authority_context)
            except ValueError as exc:
                fail(str(exc))
        try:
            result = workspace_for(root).assign_proposal_memory_scope(
                proposal_id=proposal_id,
                kind=kind,
                section_ids=section_id or [],
                operation_key=operation_key.strip() or f"local-memory-scope:{uuid.uuid4()}",
                expected_memory_revision=expected_memory_revision,
                expected_structure_revision=expected_structure_revision,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                authority_context=context,
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "proposal.scope.set",
            {"project_memory_scope_mutation": result.to_dict()},
            normalized,
        )

    @project_memory_app.command("classification")
    def classification(
        limit: int = typer.Option(100, "--limit", min=1, max=4096),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            snapshot = workspace_for(root).project_memory_classification()
            payload = snapshot.to_dict(limit=limit)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.memory.classification",
            {"memory_classification": payload},
            normalized,
        )


def _emit(operation: str, payload: dict[str, object], output_format: str) -> None:
    if output_format == "json":
        print_json(success_envelope(operation, payload))
        return
    console.print(yaml_dump_for_cli(payload), end="")


def _output_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized
