from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.governed_capabilities import governed_capability_registry_payload
from p2p_engine.services.authority import AuthorityContractCodec


def register_project_authority_commands(
    authority_app: typer.Typer,
    rotate_app: typer.Typer,
) -> None:
    authority_app.add_typer(rotate_app, name="rotate")

    @authority_app.command("show")
    def authority_show(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            descriptor = workspace_for(root).project_authority()
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_authority": descriptor.to_dict()}
        if output_format == "json":
            print_json(success_envelope("project.authority.show", payload))
            return
        if output_format != "text":
            fail("Authority show format must be text or json")
        console.print("Project authority")
        console.print(f"  id: {descriptor.authority_id}")
        console.print(f"  mode: {descriptor.mode.value}")
        console.print(f"  generation: {descriptor.generation}")
        if descriptor.provider_id:
            console.print(f"  provider: {descriptor.provider_id}")
            console.print(f"  provider policy: {descriptor.provider_policy_version}")
        else:
            console.print(f"  local policy: {descriptor.local_policy_version}")

    @authority_app.command("capabilities")
    def authority_capabilities(
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        payload = governed_capability_registry_payload()
        if output_format == "json":
            print_json(
                success_envelope(
                    "project.authority.capabilities",
                    {"governed_capabilities": payload},
                )
            )
            return
        if output_format != "text":
            fail("Authority capabilities format must be text or json")
        console.print("Governed P2P capabilities")
        for item in payload["capabilities"]:
            console.print(
                f"  {item['capability']}: {item['mutation_surface']} "
                f"({item['local_policy_rule']})"
            )

    @rotate_app.command("preview")
    def rotate_preview(
        operation_key: str = typer.Option(..., "--operation-key"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        target_mode: str = typer.Option("", "--target-mode"),
        replacement_authority_id: str = typer.Option(
            "", "--replacement-authority-id"
        ),
        provider_id: str = typer.Option("", "--provider-id"),
        provider_policy_version: str = typer.Option(
            "", "--provider-policy-version"
        ),
        display_name: str = typer.Option("", "--display-name"),
        rotated_at: str = typer.Option("", "--rotated-at"),
        authority_context: Path | None = typer.Option(
            None, "--authority-context", help="Typed external AuthorityContext JSON"
        ),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        context = _context(authority_context)
        try:
            preview = workspace_for(root).preview_project_authority_rotation(
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor_actor or actor,
                executor_kind=executor_kind,
                target_mode=target_mode,
                replacement_authority_id=replacement_authority_id,
                provider_id=provider_id,
                provider_policy_version=provider_policy_version,
                display_name=display_name,
                rotated_at=rotated_at,
                authority_context=context,
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_authority_rotation": preview.to_dict()}
        if output_format == "json":
            print_json(success_envelope("project.authority.rotate.preview", payload))
            return
        if output_format != "text":
            fail("Authority rotation preview format must be text or json")
        console.print("Project authority rotation preview")
        console.print(f"  token: {preview.mutation.preview_token}")
        console.print(f"  generation: {preview.previous_descriptor.generation} -> {preview.new_descriptor.generation}")
        console.print(f"  rotated at: {preview.rotation_request['rotated_at']}")

    @rotate_app.command("apply")
    def rotate_apply(
        operation_key: str = typer.Option(..., "--operation-key"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        rotated_at: str = typer.Option(..., "--rotated-at"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        target_mode: str = typer.Option("", "--target-mode"),
        replacement_authority_id: str = typer.Option(
            "", "--replacement-authority-id"
        ),
        provider_id: str = typer.Option("", "--provider-id"),
        provider_policy_version: str = typer.Option(
            "", "--provider-policy-version"
        ),
        display_name: str = typer.Option("", "--display-name"),
        authority_context: Path | None = typer.Option(
            None, "--authority-context", help="Exact preview AuthorityContext JSON"
        ),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        context = _context(authority_context)
        try:
            result = workspace_for(root).apply_project_authority_rotation(
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor_actor or actor,
                executor_kind=executor_kind,
                preview_token=preview_token,
                confirm=confirm,
                target_mode=target_mode,
                replacement_authority_id=replacement_authority_id,
                provider_id=provider_id,
                provider_policy_version=provider_policy_version,
                display_name=display_name,
                rotated_at=rotated_at,
                authority_context=context,
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_authority_rotation": result.to_dict()}
        if output_format == "json":
            print_json(success_envelope("project.authority.rotate.apply", payload))
            return
        if output_format != "text":
            fail("Authority rotation apply format must be text or json")
        console.print("Project authority rotation")
        console.print(f"  status: {result.status}")
        console.print(f"  generation: {result.new_descriptor.generation}")
        console.print(f"  event: {result.event_id}")

    @rotate_app.command("status")
    def rotate_status(
        operation_key: str = typer.Option(..., "--operation-key"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("json", "--format", help="text or json"),
    ) -> None:
        try:
            status = workspace_for(root).mutation_status(
                idempotency_key=operation_key
            )
        except ValueError as exc:
            fail(str(exc))
        if status.operation and status.operation != "project_authority_rotate":
            fail("P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation")
        payload = {"project_authority_rotation_status": status.to_dict()}
        if output_format == "json":
            print_json(success_envelope("project.authority.rotate.status", payload))
            return
        if output_format != "text":
            fail("Authority rotation status format must be text or json")
        console.print(f"state: {status.state}")
        console.print(f"operation: {status.operation or 'not found'}")
        console.print(f"generation: {status.result.get('new_descriptor', {}).get('generation', '-') if isinstance(status.result.get('new_descriptor'), dict) else '-'}")


def _context(path: Path | None):
    if path is None:
        return None
    try:
        return AuthorityContractCodec().context_from_path(path)
    except ValueError as exc:
        fail(str(exc))
