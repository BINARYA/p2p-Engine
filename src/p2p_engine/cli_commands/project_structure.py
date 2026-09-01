from __future__ import annotations

import uuid
from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json, success_envelope
from p2p_engine.cli_shared import console, fail, yaml_dump_for_cli
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.project_structure_merge_restore import (
    StructureElementRef,
    structure_merge_plan_from_mapping,
    structure_restore_plan_from_mapping,
)
from p2p_engine.core.project_structure_replacement import (
    structure_replacement_plan_from_mapping,
)
from p2p_engine.core.project_structure_retirement import (
    structure_retirement_plan_from_mapping,
    structure_retirement_target_from_text,
)
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.authority import AuthorityContractCodec


def register_project_structure_commands(structure_app: typer.Typer) -> None:
    retire_app = typer.Typer(help="Preview and apply governed structure retirement")
    replace_app = typer.Typer(
        help="Replace the project-owned structure from an exact vertical release"
    )
    merge_app = typer.Typer(help="Selectively merge an exact structure source")
    restore_app = typer.Typer(help="Restore a retained structure as a forward revision")
    retained_app = typer.Typer(help="Inspect retained canonical structure revisions")
    structure_app.add_typer(retire_app, name="retire")
    structure_app.add_typer(replace_app, name="replace")
    structure_app.add_typer(merge_app, name="merge")
    structure_app.add_typer(restore_app, name="restore")
    structure_app.add_typer(retained_app, name="retained")

    @retained_app.command("list")
    def retained_list(
        limit: int = typer.Option(20, "--limit", min=1, max=100),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            result = workspace_for(root).retained_project_structure_revisions(limit=limit)
        except ValueError as exc:
            fail(str(exc))
        _emit("project.structure.retained.list", {"retained_structures": result}, normalized)

    @retained_app.command("inspect")
    def retained_inspect(
        revision: int = typer.Argument(..., min=1),
        include_structure: bool = typer.Option(False, "--include-structure"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            result = workspace_for(root).inspect_retained_project_structure_revision(
                revision=revision,
                include_structure=include_structure,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit("project.structure.retained.inspect", {"retained_structure": result}, normalized)

    @merge_app.command("compare")
    def merge_compare(
        source: str = typer.Argument(..., help="Exact vertical release or .p2pbundle"),
        selected: list[str] | None = typer.Option(
            None, "--select", help="Typed ID kind:id; repeat as needed"
        ),
        limit: int = typer.Option(250, "--limit", min=1, max=1000),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            result = workspace_for(root).compare_project_structure_merge(
                source=source,
                selected=[_merge_ref(item) for item in selected or ()],
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.merge.compare",
            {"structure_comparison": result.to_dict()},
            normalized,
        )

    @merge_app.command("preview")
    def merge_preview(
        source: str = typer.Argument(..., help="Exact vertical release or .p2pbundle"),
        plan: Path = typer.Option(..., "--plan", help="Typed YAML merge plan"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        limit: int = typer.Option(250, "--limit", min=1, max=1000),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        context = _authority_context(authority_context, normalized)
        try:
            result = workspace_for(root).preview_project_structure_merge(
                source=source,
                plan=_load_merge_plan(plan),
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                authority_context=context,
                channel="cli",
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.merge.preview",
            {"project_structure_merge_preview": result.to_dict()},
            normalized,
        )

    @merge_app.command("apply")
    def merge_apply(
        source: str = typer.Argument(..., help="Exact vertical release or .p2pbundle"),
        plan: Path = typer.Option(..., "--plan", help="Typed YAML merge plan"),
        preview_token: str = typer.Option(..., "--preview-token"),
        operation_key: str = typer.Option(..., "--operation-key"),
        confirm: bool = typer.Option(False, "--confirm"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        context = _authority_context(authority_context, normalized)
        try:
            result = workspace_for(root).apply_project_structure_merge(
                source=source,
                plan=_load_merge_plan(plan),
                preview_token=preview_token,
                operation_key=operation_key,
                confirm=confirm,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                authority_context=context,
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.merge.apply",
            {"project_structure_merge": result.to_dict()},
            normalized,
        )

    @restore_app.command("preview")
    def restore_preview(
        plan: Path = typer.Option(..., "--plan", help="Typed YAML restore plan"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        limit: int = typer.Option(250, "--limit", min=1, max=1000),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        context = _authority_context(authority_context, normalized)
        try:
            result = workspace_for(root).preview_project_structure_restore(
                plan=_load_restore_plan(plan),
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                authority_context=context,
                channel="cli",
                limit=limit,
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.restore.preview",
            {"project_structure_restore_preview": result.to_dict()},
            normalized,
        )

    @restore_app.command("apply")
    def restore_apply(
        plan: Path = typer.Option(..., "--plan", help="Typed YAML restore plan"),
        preview_token: str = typer.Option(..., "--preview-token"),
        operation_key: str = typer.Option(..., "--operation-key"),
        confirm: bool = typer.Option(False, "--confirm"),
        actor: str = typer.Option("owner", "--actor"),
        executor: str = typer.Option("", "--executor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        authority_context: Path | None = typer.Option(None, "--authority-context"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        context = _authority_context(authority_context, normalized)
        try:
            result = workspace_for(root).apply_project_structure_restore(
                plan=_load_restore_plan(plan),
                preview_token=preview_token,
                operation_key=operation_key,
                confirm=confirm,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                authority_context=context,
                channel="cli",
            )
        except ValueError as exc:
            fail(str(exc))
        _emit(
            "project.structure.restore.apply",
            {"project_structure_restore": result.to_dict()},
            normalized,
        )

    for app, operation in ((merge_app, "merge"), (restore_app, "restore")):
        _register_transition_status_recover(app, operation)

    @structure_app.command("show")
    def structure_show(
        include_retired: bool = typer.Option(
            False, "--include-retired", help="Include retired structural elements"
        ),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            structure = workspace_for(root).project_structure(include_retired=include_retired)
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
        _emit(
            "project.structure.history",
            {"project_structure_history": history.to_dict()},
            normalized,
        )

    @structure_app.command("add-section")
    def add_section(
        title: str = typer.Argument(..., help="Section title"),
        expected_revision: int = typer.Option(..., "--expected-revision", min=1),
        section_id: str = typer.Option(
            "", "--id", help="Stable ID; generated from title when omitted"
        ),
        description: str = typer.Option("", "--description"),
        required: bool = typer.Option(True, "--required/--optional"),
        actor: str = typer.Option("owner", "--actor", help="Authorized project subject"),
        executor: str = typer.Option(
            "", "--executor", help="Executing identity; defaults to actor"
        ),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        operation_key: str = typer.Option(
            "", "--operation-key", help="Opaque idempotency key; required for JSON"
        ),
        authority_context: Path | None = typer.Option(
            None, "--authority-context", help="External AuthorityContext JSON; JSON mode only"
        ),
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
        element_kind: str = typer.Argument(
            ..., help="section, field, question, criterion, or artifact"
        ),
        element_id: str = typer.Argument(..., help="Stable element ID"),
        expected_revision: int = typer.Option(..., "--expected-revision", min=1),
        section_id: str | None = typer.Option(
            None, "--section", help="Section ID when a field ID is not globally unique"
        ),
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
        section_id: list[str] = typer.Option(
            ...,
            "--section-id",
            help="Active section ID in desired order; repeat for the complete set",
        ),
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
        target: list[str] = typer.Option(
            ..., "--target", help="Target as kind:id; repeat for multiple targets"
        ),
        expected_structure_revision: int = typer.Option(
            ..., "--expected-structure-revision", min=1
        ),
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
            parsed_targets = [structure_retirement_target_from_text(item) for item in target]
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
        target: list[str] = typer.Option(
            ..., "--target", help="Target as kind:id; repeat for multiple targets"
        ),
        expected_structure_revision: int = typer.Option(
            ..., "--expected-structure-revision", min=1
        ),
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
            parsed_targets = [structure_retirement_target_from_text(item) for item in target]
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
        expected_structure_revision: int = typer.Option(
            ..., "--expected-structure-revision", min=1
        ),
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
        expected_structure_revision: int = typer.Option(
            ..., "--expected-structure-revision", min=1
        ),
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


def _load_merge_plan(path: Path):
    try:
        payload = load_yaml(path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
        return structure_merge_plan_from_mapping(payload)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        fail(str(exc))


def _load_restore_plan(path: Path):
    try:
        payload = load_yaml(path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
        return structure_restore_plan_from_mapping(payload)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        fail(str(exc))


def _merge_ref(value: str) -> StructureElementRef:
    target = structure_retirement_target_from_text(value)
    return StructureElementRef(
        kind=target.kind,
        element_id=target.element_id,
        section_id=target.section_id,
    )


def _register_transition_status_recover(app: typer.Typer, operation: str) -> None:
    @app.command("status")
    def transition_status(
        operation_key: str = typer.Option(..., "--operation-key", "--idempotency-key"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        try:
            status = workspace_for(root).mutation_status(idempotency_key=operation_key)
        except ValueError as exc:
            fail(str(exc))
        _emit(
            f"project.structure.{operation}.status",
            {"mutation_status": status.to_dict()},
            normalized,
        )

    @app.command("recover")
    def transition_recover(
        transaction_id: str = typer.Argument(...),
        action: str = typer.Option(..., "--action", help="resume or rollback"),
        actor: str = typer.Option(..., "--actor"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        normalized = _output_format(output_format)
        selected = action.strip().lower()
        if selected not in {"resume", "rollback"}:
            fail("P2P_STRUCTURE_TRANSITION_RECOVERY_INVALID: --action must be resume or rollback")
        try:
            if selected == "resume":
                result = workspace_for(root).resume_workspace_transaction(
                    transaction_id=transaction_id, actor=actor, confirm=confirm
                )
            else:
                result = workspace_for(root).rollback_workspace_transaction(
                    transaction_id=transaction_id, actor=actor, confirm=confirm
                )
        except ValueError as exc:
            fail(str(exc))
        raw = result.to_dict()
        public = {
            "status": raw.get("status"),
            "operation_id": raw.get("operation_id"),
            "transaction_id": raw.get("transaction_id"),
            "recovery_required": raw.get("recovery_required"),
            "message": raw.get("message"),
        }
        _emit(
            f"project.structure.{operation}.recover",
            {"recovery": public},
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
