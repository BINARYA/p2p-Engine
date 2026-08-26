from __future__ import annotations

from pathlib import Path
import uuid

import typer

from p2p_engine.core.project_structure_retirement import (
    structure_retirement_plan_from_mapping,
    structure_retirement_target_from_text,
)
from p2p_engine.core.project_structure_replacement import (
    structure_replacement_plan_from_mapping,
)
from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail, workspace as workspace_for, yaml_dump_for_cli
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.authority import AuthorityContractCodec


def register_project_structure_commands(structure_app: typer.Typer) -> None:
    retire_app = typer.Typer(help="Preview and apply governed structure retirement")
    replace_app = typer.Typer(help="Replace the project-owned structure from an exact vertical release")
    structure_app.add_typer(retire_app, name="retire")
    structure_app.add_typer(replace_app, name="replace")

    @structure_app.command("show")
    def structure_show(
        include_retired: bool = typer.Option(False, "--include-retired", help="Include retired structural elements"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            structure = workspace_for(root).project_structure(
                include_retired=include_retired
            )
        except ValueError as exc:
            fail(str(exc))
        payload = {"project_structure": structure.to_dict(include_retired=include_retired)}
        _emit("project.structure.show", payload, normalized)

    @structure_app.command("history")
    def structure_history(
        limit: int = typer.Option(20, "--limit", min=1, max=100, help="Maximum newest events"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            history = workspace_for(root).project_structure_history(limit=limit)
        except ValueError as exc:
            fail(str(exc))
        _emit("project.structure.history", {"project_structure_history": history.to_dict()}, normalized)

    @structure_app.command("add-section")
    def add_section(
        title: str = typer.Argument(..., help="Section title"),
        expected_revision: int = typer.Option(..., "--expected-revision", min=1),
        section_id: str = typer.Option("", "--id", help="Stable ID; generated from title when omitted"),
        description: str = typer.Option("", "--description"),
        required: bool = typer.Option(True, "--required/--optional"),
        actor: str = typer.Option("owner", "--actor", help="Authorized project subject"),
        executor: str = typer.Option("", "--executor", help="Executing identity; defaults to actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        operation_key: str = typer.Option("", "--operation-key", help="Opaque idempotency key; required for JSON"),
        authority_context: Path | None = typer.Option(None, "--authority-context", help="External AuthorityContext JSON; JSON mode only"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        request: dict[str, object] = {
            "title": title,
            "description": description,
            "required": required,
        }
        if section_id:
            request["section_id"] = section_id
        _change(
            root=root,
            operation="add_section",
            expected_revision=expected_revision,
            request=request,
            actor=actor,
            executor=executor,
            executor_kind=executor_kind,
            operation_key=operation_key,
            authority_context=authority_context,
            output_format=output_format,
            public_operation="project.structure.add-section",
        )

    @structure_app.command("update-metadata")
    def update_metadata(
        element_kind: str = typer.Argument(..., help="section, field, question, criterion, or artifact"),
        element_id: str = typer.Argument(..., help="Stable element ID"),
        expected_revision: int = typer.Option(..., "--expected-revision", min=1),
        section_id: str | None = typer.Option(None, "--section", help="Section ID when a field ID is not globally unique"),
        title: str | None = typer.Option(None, "--title"),
        description: str | None = typer.Option(None, "--description"),
        required: bool | None = typer.Option(None, "--required/--optional"),
        enabled: bool | None = typer.Option(None, "--enabled/--disabled"),
        priority: str | None = typer.Option(None, "--priority"),
        keyword: list[str] | None = typer.Option(None, "--keyword"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        operation_key: str = typer.Option("", "--operation-key"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        request: dict[str, object] = {
            "element_kind": element_kind,
            "element_id": element_id,
        }
        if section_id is not None:
            request["section_id"] = section_id
        for key, value in (
            ("title", title),
            ("description", description),
            ("required", required),
            ("enabled", enabled),
            ("priority", priority),
        ):
            if value is not None:
                request[key] = value
        if keyword is not None:
            request["keywords"] = keyword
        _change(
            root=root,
            operation="update_metadata",
            expected_revision=expected_revision,
            request=request,
            actor=actor,
            executor=executor,
            executor_kind=executor_kind,
            operation_key=operation_key,
            authority_context=authority_context,
            output_format=output_format,
            public_operation="project.structure.update-metadata",
        )

    @structure_app.command("reorder")
    def reorder_sections(
        section_id: list[str] = typer.Option(..., "--section-id", help="Active section ID in desired order; repeat for the complete set"),
        expected_revision: int = typer.Option(..., "--expected-revision", min=1),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        operation_key: str = typer.Option("", "--operation-key"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        _change(
            root=root,
            operation="reorder_sections",
            expected_revision=expected_revision,
            request={"section_ids": section_id},
            actor=actor,
            executor=executor,
            executor_kind=executor_kind,
            operation_key=operation_key,
            authority_context=authority_context,
            output_format=output_format,
            public_operation="project.structure.reorder",
        )

    @retire_app.command("preview")
    def retire_preview(
        target: list[str] = typer.Option(..., "--target", help="Target as kind:id; repeat for multiple targets"),
        expected_structure_revision: int = typer.Option(..., "--expected-structure-revision", min=1),
        expected_memory_revision: str = typer.Option(..., "--expected-memory-revision"),
        plan: Path | None = typer.Option(None, "--plan", help="YAML disposition plan"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        limit: int = typer.Option(100, "--limit", min=1, max=1000),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        context = _authority_context(authority_context, normalized)
        try:
            parsed_targets = [
                structure_retirement_target_from_text(item) for item in target
            ]
            parsed_plan = _load_retirement_plan(plan)
            preview = workspace_for(root).preview_project_structure_retirement(
                targets=parsed_targets,
                expected_structure_revision=expected_structure_revision,
                expected_memory_revision=expected_memory_revision,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                plan=parsed_plan,
                authority_context=context,
                channel="cli",
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.retire.preview",
            {"project_structure_retirement_preview": preview.to_dict()},
            normalized,
        )

    @retire_app.command("apply")
    def retire_apply(
        target: list[str] = typer.Option(..., "--target", help="Target as kind:id; repeat for multiple targets"),
        expected_structure_revision: int = typer.Option(..., "--expected-structure-revision", min=1),
        expected_memory_revision: str = typer.Option(..., "--expected-memory-revision"),
        preview_token: str = typer.Option(..., "--preview-token"),
        operation_key: str = typer.Option(..., "--operation-key"),
        plan: Path | None = typer.Option(None, "--plan", help="YAML disposition plan"),
        confirm: bool = typer.Option(False, "--confirm"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        limit: int = typer.Option(100, "--limit", min=1, max=1000),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        if not operation_key.strip():
            fail("P2P_IDEMPOTENCY_KEY_REQUIRED: retirement apply requires --operation-key")
        context = _authority_context(authority_context, normalized)
        try:
            parsed_targets = [
                structure_retirement_target_from_text(item) for item in target
            ]
            parsed_plan = _load_retirement_plan(plan)
            result = workspace_for(root).apply_project_structure_retirement(
                targets=parsed_targets,
                expected_structure_revision=expected_structure_revision,
                expected_memory_revision=expected_memory_revision,
                preview_token=preview_token,
                operation_key=operation_key,
                confirm=confirm,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                plan=parsed_plan,
                authority_context=context,
                channel="cli",
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.retire.apply",
            {"project_structure_retirement": result.to_dict()},
            normalized,
        )

    @retire_app.command("status")
    def retire_status(
        operation_key: str = typer.Option(..., "--operation-key", "--idempotency-key"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            status = workspace_for(root).mutation_status(
                idempotency_key=operation_key,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.retire.status",
            {"mutation_status": status.to_dict()},
            normalized,
        )

    @replace_app.command("preview")
    def replace_preview(
        target: str = typer.Argument(..., help="Exact release coordinate or local portable pack"),
        expected_structure_revision: int = typer.Option(..., "--expected-structure-revision", min=1),
        expected_memory_revision: str = typer.Option(..., "--expected-memory-revision"),
        plan: Path | None = typer.Option(None, "--plan", help="YAML replacement disposition plan"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        limit: int = typer.Option(100, "--limit", min=1, max=1000),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        context = _authority_context(authority_context, normalized)
        try:
            parsed_plan = _load_replacement_plan(plan)
            preview = workspace_for(root).preview_project_structure_replacement(
                target=target,
                expected_structure_revision=expected_structure_revision,
                expected_memory_revision=expected_memory_revision,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                plan=parsed_plan,
                authority_context=context,
                channel="cli",
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.replace.preview",
            {"project_structure_replacement_preview": preview.to_dict()},
            normalized,
        )

    @replace_app.command("apply")
    def replace_apply(
        target: str = typer.Argument(..., help="Exact release coordinate or local portable pack"),
        expected_structure_revision: int = typer.Option(..., "--expected-structure-revision", min=1),
        expected_memory_revision: str = typer.Option(..., "--expected-memory-revision"),
        preview_token: str = typer.Option(..., "--preview-token"),
        operation_key: str = typer.Option(..., "--operation-key"),
        plan: Path = typer.Option(..., "--plan", help="YAML replacement disposition plan"),
        confirm: bool = typer.Option(False, "--confirm"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        limit: int = typer.Option(100, "--limit", min=1, max=1000),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        if not operation_key.strip():
            fail("P2P_IDEMPOTENCY_KEY_REQUIRED: replacement apply requires --operation-key")
        context = _authority_context(authority_context, normalized)
        try:
            parsed_plan = _load_replacement_plan(plan)
            result = workspace_for(root).apply_project_structure_replacement(
                target=target,
                expected_structure_revision=expected_structure_revision,
                expected_memory_revision=expected_memory_revision,
                preview_token=preview_token,
                operation_key=operation_key,
                confirm=confirm,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                plan=parsed_plan,
                authority_context=context,
                channel="cli",
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.replace.apply",
            {"project_structure_replacement": result.to_dict()},
            normalized,
        )

    @replace_app.command("status")
    def replace_status(
        operation_key: str = typer.Option(..., "--operation-key", "--idempotency-key"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            status = workspace_for(root).mutation_status(
                idempotency_key=operation_key,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.replace.status",
            {"mutation_status": status.to_dict()},
            normalized,
        )


def _change(
    *,
    root: Path,
    operation: str,
    expected_revision: int,
    request: dict[str, object],
    actor: str,
    executor: str,
    executor_kind: str,
    operation_key: str,
    authority_context: Path | None,
    output_format: str,
    public_operation: str,
) -> None:
    normalized = _output_format(output_format)
    if normalized == "json" and not operation_key.strip():
        fail("P2P_IDEMPOTENCY_KEY_REQUIRED: JSON structure mutation requires --operation-key")
    if normalized != "json" and authority_context is not None:
        fail("P2P_AUTHORITY_CONTEXT_INVALID: --authority-context requires --format json")
    context = None
    if authority_context is not None:
        try:
            context = AuthorityContractCodec().context_from_path(authority_context)
        except ValueError as exc:
            fail(str(exc))
    try:
        result = workspace_for(root).change_project_structure(
            operation=operation,
            operation_key=operation_key.strip() or f"local-structure:{uuid.uuid4()}",
            expected_revision=expected_revision,
            actor_id=actor,
            executor_id=executor or actor,
            executor_kind=executor_kind,
            request=request,
            authority_context=context,
            channel="cli",
        )
    except ValueError as exc:
        fail(str(exc))
    _emit(public_operation, {"project_structure_mutation": result.to_dict()}, normalized)


def _authority_context(
    authority_context: Path | None,
    output_format: str,
):
    if output_format != "json" and authority_context is not None:
        fail("P2P_AUTHORITY_CONTEXT_INVALID: --authority-context requires --format json")
    if authority_context is None:
        return None
    try:
        return AuthorityContractCodec().context_from_path(authority_context)
    except ValueError as exc:
        fail(str(exc))


def _load_retirement_plan(path: Path | None):
    if path is None:
        return None
    try:
        payload = load_yaml(
            path.read_bytes(),
            loader_contract=UNIQUE_LOADER_CONTRACT,
        )
        return structure_retirement_plan_from_mapping(payload)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        fail(str(exc))


def _load_replacement_plan(path: Path | None):
    if path is None:
        return None
    try:
        payload = load_yaml(
            path.read_bytes(),
            loader_contract=UNIQUE_LOADER_CONTRACT,
        )
        return structure_replacement_plan_from_mapping(payload)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        fail(str(exc))


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
