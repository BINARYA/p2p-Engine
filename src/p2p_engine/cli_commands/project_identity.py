from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.services.authority import AuthorityContractCodec


def register_project_identity_commands(project_app: typer.Typer) -> None:
    identity_app = typer.Typer(help="Inspect and govern stable storage-neutral project identity")
    adopt_app = typer.Typer(help="Explicitly adopt identity for a legacy project")
    derive_app = typer.Typer(help="Create a new independent identity in this copied workspace")
    identity_app.add_typer(adopt_app, name="adopt")
    identity_app.add_typer(derive_app, name="derive")
    project_app.add_typer(identity_app, name="identity")

    @identity_app.command("show")
    def identity_show(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            identity = workspace_for(root).project_identity()
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_identity": identity.to_dict()}
        _emit("project.identity.show", payload, output_format, _identity_text(identity))

    @identity_app.command("status")
    def identity_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        status = workspace_for(root).project_identity_status()
        payload = {"project_identity_status": status.to_dict()}
        lines = [
            "Project identity status",
            f"  state: {status.state}",
            f"  mutable: {'yes' if status.mutable else 'no'}",
        ]
        if status.identity is not None:
            lines.extend(_identity_text(status.identity).splitlines()[1:])
        for blocker in status.blockers:
            lines.append(f"  blocker: {blocker}")
        if status.suggested_command:
            lines.append(f"  recovery: {status.suggested_command}")
        _emit("project.identity.status", payload, output_format, "\n".join(lines))

    @identity_app.command("transitions")
    def identity_transitions(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        matrix = workspace_for(root).project_identity_transition_matrix()
        payload = {"identity_transitions": matrix}
        lines = ["Project identity transition matrix"]
        for item in matrix:
            lines.append(
                "  {operation}: project={project_uuid}, replica={replica_id}, "
                "binding={remote_binding}".format(**item)
            )
        _emit("project.identity.transitions", payload, output_format, "\n".join(lines))

    @identity_app.command("copy-check")
    def identity_copy_check(
        observed_project_uuid: str = typer.Option(..., "--observed-project-uuid"),
        observed_replica_id: str = typer.Option("", "--observed-replica-id"),
        intent: str = typer.Option(
            "",
            "--intent",
            help="same-instance, new-replica, read-only, or derive",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).assess_project_copy(
                observed_project_uuid=observed_project_uuid,
                observed_replica_id=observed_replica_id,
                intent=intent,
            )
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_copy_assessment": result.to_dict()}
        lines = [
            "Project copy assessment",
            f"  state: {result.state}",
            f"  allowed: {'yes' if result.allowed else 'no'}",
        ]
        lines.extend(f"  next: {item}" for item in result.next_actions)
        _emit("project.identity.copy-check", payload, output_format, "\n".join(lines))

    @adopt_app.command("preview")
    def adoption_preview(
        operation_key: str = typer.Option(..., "--operation-key"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            preview = workspace_for(root).preview_project_identity_adoption(
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor_actor or actor,
                executor_kind=executor_kind,
                authority_context=_context(authority_context),
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_identity_adoption": preview.to_dict()}
        _emit(
            "project.identity.adopt.preview",
            payload,
            output_format,
            "\n".join(
                [
                    "Project identity adoption preview",
                    f"  project UUID: {preview.candidate.project_uuid.value}",
                    f"  replica ID: {preview.candidate.replica_id}",
                    f"  backup: {preview.backup_path}",
                    f"  token: {preview.mutation.preview_token}",
                ]
            ),
        )

    @adopt_app.command("apply")
    def adoption_apply(
        operation_key: str = typer.Option(..., "--operation-key"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).apply_project_identity_adoption(
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor_actor or actor,
                executor_kind=executor_kind,
                preview_token=preview_token,
                confirm=confirm,
                authority_context=_context(authority_context),
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        _emit_result("project.identity.adopt.apply", result, output_format)

    @derive_app.command("preview")
    def derivation_preview(
        operation_key: str = typer.Option(..., "--operation-key"),
        name: str = typer.Option("", "--name", help="Optional derived display name"),
        retain_lineage: bool = typer.Option(True, "--retain-lineage/--no-retain-lineage"),
        lineage_visibility: str = typer.Option(
            "preserved", "--lineage-visibility", help="preserved or private"
        ),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            preview = workspace_for(root).preview_project_identity_derivation(
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor_actor or actor,
                executor_kind=executor_kind,
                display_name=name,
                retain_lineage=retain_lineage,
                lineage_visibility=lineage_visibility,
                authority_context=_context(authority_context),
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_identity_derivation": preview.to_dict()}
        _emit(
            "project.identity.derive.preview",
            payload,
            output_format,
            "\n".join(
                [
                    "Project identity derivation preview",
                    f"  source UUID: {preview.previous.project_uuid.value if preview.previous else '-'}",
                    f"  derived UUID: {preview.candidate.project_uuid.value}",
                    f"  lineage retained: {'yes' if retain_lineage else 'no'}",
                    f"  token: {preview.mutation.preview_token}",
                ]
            ),
        )

    @derive_app.command("apply")
    def derivation_apply(
        operation_key: str = typer.Option(..., "--operation-key"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        name: str = typer.Option("", "--name"),
        retain_lineage: bool = typer.Option(True, "--retain-lineage/--no-retain-lineage"),
        lineage_visibility: str = typer.Option("preserved", "--lineage-visibility"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        root: Path = typer.Option(Path.cwd(), "--root"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
    ) -> None:
        try:
            result = workspace_for(root).apply_project_identity_derivation(
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor_actor or actor,
                executor_kind=executor_kind,
                preview_token=preview_token,
                confirm=confirm,
                display_name=name,
                retain_lineage=retain_lineage,
                lineage_visibility=lineage_visibility,
                authority_context=_context(authority_context),
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        _emit_result("project.identity.derive.apply", result, output_format)


def _context(path: Path | None):
    if path is None:
        return None
    try:
        return AuthorityContractCodec().context_from_path(path)
    except ValueError as exc:
        fail(str(exc))


def _identity_text(identity) -> str:
    binding = identity.remote_binding
    return "\n".join(
        [
            "Project identity",
            f"  project UUID: {identity.project_uuid.value}",
            f"  display name: {identity.display_name}",
            f"  mode: {identity.mode.value}",
            f"  replica ID: {identity.replica_id or '-'}",
            f"  remote server: {binding.server_instance_id if binding else '-'}",
            f"  remote project: {binding.remote_project_id if binding else '-'}",
            f"  lineage entries: {len(identity.lineage)}",
        ]
    )


def _emit_result(operation: str, result, output_format: str) -> None:
    payload = {"project_identity_mutation": result.to_dict()}
    _emit(
        operation,
        payload,
        output_format,
        "\n".join(
            [
                "Project identity mutation",
                f"  status: {result.status}",
                f"  kind: {result.kind}",
                f"  project UUID: {result.current.project_uuid.value}",
                f"  message: {result.message}",
            ]
        ),
    )


def _emit(operation: str, payload: dict[str, object], output_format: str, text: str) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        print_json(success_envelope(operation, payload))
        return
    if normalized != "text":
        fail("Identity output format must be text or json")
    console.print(text)
