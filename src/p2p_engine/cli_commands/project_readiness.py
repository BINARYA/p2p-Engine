from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

import typer
import yaml

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.foundation.yaml_loaders import load_yaml


PROJECT_QUESTION_ANSWER_MAX_BYTES = 64 * 1024


def register_project_readiness_commands(
    readiness_app: typer.Typer,
    questions_app: typer.Typer,
) -> None:
    @readiness_app.command("review")
    def review(
        vertical: str | None = typer.Option(None, "--vertical"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        limit: int = typer.Option(10, "--limit", min=1, max=100),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """Review bounded project-readiness gaps and vertical sections."""
        try:
            workspace = workspace_for(root)
            result = workspace.review_project_readiness(vertical)
            page = workspace.project_readiness_gaps(limit=limit)
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_readiness_review")
        payload = {
            "project_readiness": {
                "mutation_performed": False,
                "active_vertical_id": result.active_vertical_id,
                "vertical_source": result.vertical_source,
                "fallback_used": result.fallback_used,
                "snapshot_fingerprint": result.snapshot_fingerprint,
                "gap_counts": result.gap_counts,
                "gaps": page.to_dict(),
                "sections": [_jsonable(item) for item in result.sections],
                "missing_capisaldi": result.missing_capisaldi,
                "unmapped_proposals": result.unmapped_proposals,
                "unmapped_proposals_total": result.unmapped_proposals_total,
                "unmapped_proposals_truncated": result.unmapped_proposals_truncated,
                "suggested_next": result.suggested_next,
            }
        }
        if output_format == "json":
            _print_json(payload)
            return
        console.print("Project readiness review")
        console.print(f"  active_vertical: {result.active_vertical_id}")
        console.print(f"  source: {result.vertical_source}")
        console.print(f"  fallback_used: {str(result.fallback_used).lower()}")
        console.print(f"  snapshot: {result.snapshot_fingerprint}")
        console.print("Sections:")
        for section in result.sections:
            console.print(
                f"  - {section.section_id}  definition: {section.definition_status}  "
                f"evidence: {section.status}"
            )
        console.print("Missing capisaldi:")
        for section_id in result.missing_capisaldi:
            console.print(f"  - {section_id}")
        if not result.missing_capisaldi:
            console.print("  none")
        console.print(
            f"Unmapped proposals: showing {len(result.unmapped_proposals)} "
            f"of {result.unmapped_proposals_total}"
        )
        console.print(
            f"Generated questions: showing {len(result.generated_questions)} "
            f"of {result.generated_questions_total}"
        )
        console.print("Gap summary:")
        for kind, count in sorted(result.gap_counts.items()):
            console.print(f"  {kind}: {count}")
        console.print(f"Top gaps: showing {len(page.items)} of {page.total}")
        for gap in page.items:
            console.print(
                f"  - {gap.gap_id}  {gap.severity.value}  {gap.kind.value}  "
                f"{gap.section_id or gap.target_id}"
            )
        if page.truncated:
            console.print("  truncated: true")
        console.print("Suggested next:")
        for command in result.suggested_next:
            console.print(f"  - {command}")

    @readiness_app.command("gaps")
    def gaps(
        kind: str = typer.Option("", "--kind"),
        severity: str = typer.Option("", "--severity"),
        limit: int = typer.Option(20, "--limit", min=1, max=100),
        cursor: str = typer.Option("", "--cursor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """List prioritized readiness gaps with snapshot-bound pagination."""
        try:
            page = workspace_for(root).project_readiness_gaps(
                kind=kind,
                severity=severity,
                limit=limit,
                cursor=cursor,
            )
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_readiness_gaps")
        if output_format == "json":
            _print_json({"project_readiness_page": {"mutation_performed": False, **page.to_dict()}})
            return
        console.print(f"Project readiness gaps: showing {len(page.items)} of {page.total}")
        for gap in page.items:
            console.print(f"  {gap.gap_id}  {gap.severity.value}  {gap.kind.value}  {gap.rationale}")
        if page.next_cursor:
            console.print(f"next_cursor: {page.next_cursor}")

    @readiness_app.command("gap")
    def gap_show(
        gap_id: str = typer.Argument(...),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """Show one stable readiness gap."""
        try:
            gap = workspace_for(root).project_readiness_gap(gap_id)
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_readiness_gap_show")
        if output_format == "json":
            _print_json({"project_readiness_gap": {"mutation_performed": False, **gap.to_dict()}})
            return
        console.print(f"Project readiness gap {gap.gap_id}")
        console.print(f"  kind: {gap.kind.value}")
        console.print(f"  severity: {gap.severity.value}")
        console.print(f"  rationale: {gap.rationale}")
        console.print(f"  next: {gap.next_operation}")

    @questions_app.command("status")
    def question_status(
        state: str = typer.Option("", "--state"),
        limit: int = typer.Option(20, "--limit", min=1, max=100),
        cursor: str = typer.Option("", "--cursor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """List project questions without changing lifecycle state."""
        try:
            page = workspace_for(root).project_questions_page(
                state=state,
                limit=limit,
                cursor=cursor,
            )
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_questions_status")
        if output_format == "json":
            _print_json({"project_questions": {"mutation_performed": False, **page.to_dict()}})
            return
        console.print(f"Project questions: showing {len(page.items)} of {page.total}")
        for question in page.items:
            console.print(
                f"  {question.question_id}  r{question.revision}  {question.state.value}  "
                f"{question.section_id}  {question.question}"
            )
        if page.next_cursor:
            console.print(f"next_cursor: {page.next_cursor}")

    @questions_app.command("next")
    def question_next(
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """Show the next applicable unanswered project question."""
        try:
            question = workspace_for(root).next_project_question()
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_questions_next")
        payload = {
            "project_question": {
                "mutation_performed": False,
                "question": _jsonable(question) if question is not None else None,
            }
        }
        if output_format == "json":
            _print_json(payload)
            return
        if question is None:
            console.print("No applicable project question.")
            return
        console.print(f"Project question {question.question_id}")
        console.print(f"  revision: {question.revision}")
        console.print(f"  section: {question.section_id}")
        console.print(f"  question: {question.question}")

    @questions_app.command("answer")
    def question_answer(
        question_id: str = typer.Argument(...),
        value: str | None = typer.Option(None, "--value"),
        input_path: Path | None = typer.Option(None, "--input"),
        actor: str = typer.Option(..., "--actor"),
        expected_revision: int = typer.Option(..., "--expected-revision", min=1),
        replace_answer: bool = typer.Option(False, "--replace"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """Record or explicitly replace a direct owner answer."""
        if (value is None) == (input_path is None):
            fail("Provide exactly one of --value or --input.")
        try:
            if input_path is not None:
                values, evidence_refs = _load_answer_file(
                    root,
                    input_path,
                    question_id=question_id,
                    expected_revision=expected_revision,
                )
            else:
                values, evidence_refs = {"value": value}, ()
            result = workspace_for(root).answer_project_question(
                question_id,
                values=values,
                actor=actor,
                expected_revision=expected_revision,
                replace_answer=replace_answer,
                evidence_refs=evidence_refs,
            )
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_questions_answer")
        _emit_mutation("project_question", result, output_format)

    for name in ("defer", "mute", "reopen"):
        _register_reason_transition(questions_app, name)

    @questions_app.command("reconcile-preview")
    def reconcile_preview(
        actor: str = typer.Option(..., "--actor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        try:
            result = workspace_for(root).preview_project_question_reconciliation(actor=actor)
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_questions_reconcile_preview")
        _emit("project_question_reconciliation", result.to_dict(), output_format)

    @questions_app.command("reconcile-apply")
    def reconcile_apply(
        preview_token: str = typer.Option(..., "--preview-token"),
        actor: str = typer.Option(..., "--actor"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        try:
            result = workspace_for(root).apply_project_question_reconciliation(
                actor=actor,
                preview_token=preview_token,
                confirm=confirm,
            )
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_questions_reconcile_apply")
        _emit_result("project_question_reconciliation", result, output_format)

    @readiness_app.command("preview")
    def convergence_preview(
        question: list[str] = typer.Option(..., "--question"),
        actor: str = typer.Option(..., "--actor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        try:
            result = workspace_for(root).preview_project_readiness_convergence(question, actor=actor)
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_readiness_convergence_preview")
        _emit("project_readiness_preview", result.to_dict(), output_format)

    @readiness_app.command("apply")
    def convergence_apply(
        question: list[str] = typer.Option(..., "--question"),
        preview_token: str = typer.Option(..., "--preview-token"),
        actor: str = typer.Option(..., "--actor"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        try:
            result = workspace_for(root).apply_project_readiness_convergence(
                question,
                actor=actor,
                preview_token=preview_token,
                confirm=confirm,
            )
        except ValueError as exc:
            _fail_operation(exc, output_format, "project_readiness_convergence_apply")
        _emit_result("project_readiness_apply", result, output_format)


def _register_reason_transition(app: typer.Typer, operation: str) -> None:
    @app.command(operation)
    def command(
        question_id: str = typer.Argument(...),
        reason: str = typer.Option(..., "--reason"),
        actor: str = typer.Option(..., "--actor"),
        expected_revision: int = typer.Option(..., "--expected-revision", min=1),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        try:
            workspace = workspace_for(root)
            method = {
                "defer": workspace.defer_project_question,
                "mute": workspace.mute_project_question,
                "reopen": workspace.reopen_project_question,
            }[operation]
            result = method(
                question_id,
                actor=actor,
                expected_revision=expected_revision,
                reason=reason,
            )
        except ValueError as exc:
            _fail_operation(exc, output_format, f"project_questions_{operation}")
        _emit_mutation("project_question", result, output_format)


def _load_answer_file(
    root: Path,
    source: Path,
    *,
    question_id: str,
    expected_revision: int,
) -> tuple[dict[str, object], tuple[str, ...]]:
    resolved_root = root.resolve()
    if ".." in source.parts:
        raise ValueError("Answer input path cannot contain parent traversal.")
    candidate = source if source.is_absolute() else resolved_root / source
    lexical = candidate.absolute()
    if not lexical.is_relative_to(resolved_root):
        raise ValueError("Answer input must be inside the project root.")
    current = resolved_root
    for part in lexical.relative_to(resolved_root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Answer input path cannot contain symlinks.")
    resolved = lexical.resolve()
    if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
        raise ValueError("Answer input must be a regular non-symlink file inside the project root.")
    if resolved.stat().st_size > PROJECT_QUESTION_ANSWER_MAX_BYTES:
        raise ValueError(
            "P2P353_READINESS_PAYLOAD_LIMIT: answer input exceeds 64 KiB."
        )
    try:
        payload = load_yaml(resolved.read_bytes())
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Invalid project question answer input: {exc}") from exc
    if not isinstance(payload, Mapping) or set(payload) != {"project_question_answer"}:
        raise ValueError("Answer input requires one `project_question_answer` mapping.")
    answer = payload["project_question_answer"]
    if not isinstance(answer, Mapping):
        raise ValueError("project_question_answer must be a mapping.")
    allowed = {"schema_version", "question_id", "expected_revision", "values", "evidence_refs"}
    unknown = set(answer) - allowed
    if unknown:
        raise ValueError(f"Unknown project question answer fields: {sorted(unknown)}")
    if _safe_int(answer.get("schema_version"), field="schema_version") != 1:
        raise ValueError("Unsupported project question answer schema_version.")
    if str(answer.get("question_id") or "") != question_id:
        raise ValueError("Answer input question_id does not match the command argument.")
    if _safe_int(answer.get("expected_revision"), field="expected_revision") != expected_revision:
        raise ValueError("Answer input expected_revision does not match the command option.")
    values = answer.get("values")
    evidence_refs = answer.get("evidence_refs", [])
    if not isinstance(values, Mapping):
        raise ValueError("Answer input values must be a mapping.")
    if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
        raise ValueError("Answer input evidence_refs must be a string sequence.")
    normalized_refs: list[str] = []
    for item in evidence_refs:
        normalized = item.strip()
        if not normalized or len(normalized) > 512 or "\x00" in normalized or "\n" in normalized:
            raise ValueError("Answer input evidence_refs contain an invalid reference.")
        normalized_refs.append(normalized)
    return dict(values), tuple(normalized_refs)


def _safe_int(value: object, *, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Answer input `{field}` must be an integer.") from exc


def _emit_mutation(wrapper: str, result: object, output_format: str) -> None:
    payload = result.to_dict()
    _emit(wrapper, payload, output_format)
    if str(payload.get("status") or "") not in {"applied", "already_applied"}:
        raise typer.Exit(code=1)


def _emit_result(wrapper: str, result: object, output_format: str) -> None:
    payload = result.to_dict()
    _emit(wrapper, payload, output_format)
    if str(payload.get("status") or "") not in {"applied", "already_applied"}:
        raise typer.Exit(code=1)


def _emit(wrapper: str, payload: Mapping[str, object], output_format: str) -> None:
    if output_format == "json":
        _print_json({wrapper: payload})
        return
    console.print(wrapper.replace("_", " ").title())
    for key in ("status", "operation_id", "actor", "preview_token", "mutation_performed", "message"):
        if key in payload and payload[key] not in (None, ""):
            console.print(f"  {key}: {payload[key]}")
    preview = payload.get("preview")
    if isinstance(preview, Mapping) and preview.get("preview_token"):
        console.print(f"  preview_token: {preview['preview_token']}")


def _print_json(payload: object) -> None:
    console.print(json.dumps(_jsonable(payload), indent=2, sort_keys=True), soft_wrap=True)


def _fail_operation(error: ValueError, output_format: str, operation: str) -> None:
    message = str(error)
    match = re.search(r"\b(P2P[0-9]{3}_[A-Z0-9_]+)\b", message)
    if output_format == "json":
        _print_json(
            {
                "error": {
                    "code": match.group(1) if match else "P2P_PROJECT_READINESS_ERROR",
                    "operation": operation,
                    "status": "error",
                    "message": message,
                    "mutation_performed": False,
                }
            }
        )
        raise typer.Exit(code=1)
    fail(message)


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
