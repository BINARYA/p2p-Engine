from __future__ import annotations

from pathlib import Path
import uuid

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail, workspace as workspace_for, yaml_dump_for_cli
from p2p_engine.core.project_domain import ProjectDomainRef
from p2p_engine.services.authority import AuthorityContractCodec


def register_project_domain_commands(domain_app: typer.Typer) -> None:
    @domain_app.command("show")
    def domain_show(
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        normalized = _output_format(output_format)
        workspace = workspace_for(root)
        try:
            payload = {
                "project_domain": workspace.project_domain().to_dict(),
                "structure_source": workspace.project_structure_source(),
            }
        except ValueError as exc:
            fail(str(exc))
        if normalized == "json":
            print_json(success_envelope("project.domain.show", payload))
            return
        console.print(yaml_dump_for_cli(payload), end="")

    @domain_app.command("set")
    def domain_set(
        key: str = typer.Argument(..., help="Free project domain key"),
        name: str = typer.Option("", "--name", help="Display name; derived from key when omitted"),
        source: str = typer.Option("local", "--source", help="local, external, imported, or system"),
        external_ref: str | None = typer.Option(None, "--external-ref", help="Optional opaque provider reference"),
        actor: str = typer.Option("owner", "--actor", help="Authorized project subject"),
        executor: str = typer.Option("", "--executor", help="Executing identity; defaults to actor"),
        executor_kind: str = typer.Option("person", "--executor-kind", help="person, user, agent, mcp_client, or client"),
        operation_key: str = typer.Option("", "--operation-key", help="Opaque idempotency key; required for JSON"),
        authority_context: Path | None = typer.Option(None, "--authority-context", help="External AuthorityContext JSON; JSON mode only"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        try:
            descriptor = ProjectDomainRef(
                key=key,
                name=name or key.replace("_", " ").replace("-", " ").title(),
                source=source,
                external_ref=external_ref,
            )
        except ValueError as exc:
            fail(str(exc))
        _change(
            root=root,
            operation="set",
            descriptor=descriptor,
            actor=actor,
            executor=executor,
            executor_kind=executor_kind,
            operation_key=operation_key,
            authority_context=authority_context,
            output_format=output_format,
        )

    @domain_app.command("clear")
    def domain_clear(
        actor: str = typer.Option("owner", "--actor", help="Authorized project subject"),
        executor: str = typer.Option("", "--executor", help="Executing identity; defaults to actor"),
        executor_kind: str = typer.Option("person", "--executor-kind", help="person, user, agent, mcp_client, or client"),
        operation_key: str = typer.Option("", "--operation-key", help="Opaque idempotency key; required for JSON"),
        authority_context: Path | None = typer.Option(None, "--authority-context", help="External AuthorityContext JSON; JSON mode only"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        _change(
            root=root,
            operation="clear",
            descriptor=None,
            actor=actor,
            executor=executor,
            executor_kind=executor_kind,
            operation_key=operation_key,
            authority_context=authority_context,
            output_format=output_format,
        )


def _change(
    *,
    root: Path,
    operation: str,
    descriptor: ProjectDomainRef | None,
    actor: str,
    executor: str,
    executor_kind: str,
    operation_key: str,
    authority_context: Path | None,
    output_format: str,
) -> None:
    normalized = _output_format(output_format)
    if normalized == "json" and not operation_key.strip():
        fail("P2P_IDEMPOTENCY_KEY_REQUIRED: JSON domain mutation requires --operation-key")
    if normalized != "json" and authority_context is not None:
        fail("P2P_AUTHORITY_CONTEXT_INVALID: --authority-context requires --format json")
    context = None
    if authority_context is not None:
        try:
            context = AuthorityContractCodec().context_from_path(authority_context)
        except ValueError as exc:
            fail(str(exc))
    key = operation_key.strip() or f"local-domain:{uuid.uuid4()}"
    try:
        result = workspace_for(root).change_project_domain(
            operation=operation,
            operation_key=key,
            actor_id=actor,
            executor_id=executor or actor,
            executor_kind=executor_kind,
            descriptor=descriptor,
            authority_context=context,
            channel="cli",
        )
    except ValueError as exc:
        fail(str(exc))
    payload = {"project_domain_mutation": result.to_dict()}
    if normalized == "json":
        print_json(success_envelope(f"project.domain.{operation}", payload))
        return
    console.print(yaml_dump_for_cli(payload), end="")


def _output_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized
