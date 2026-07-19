from __future__ import annotations

import json
from pathlib import Path

import typer

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.workspace_schema import (
    LAYOUT_AHEAD,
    LAYOUT_INVALID,
    LAYOUT_UNSUPPORTED,
    MIGRATION_STATUS_APPLIED,
    MIGRATION_STATUS_NO_OP,
)
from p2p_engine.services.workspace_compatibility import load_owner_input_patch


def register_workspace_migration_commands(
    schema_app: typer.Typer,
    migrate_app: typer.Typer,
    recovery_app: typer.Typer,
) -> None:
    @schema_app.command("status")
    def schema_status(
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show read-only workspace schema and alignment status."""
        try:
            status = workspace_for(root).workspace_schema_status()
        except ValueError as exc:
            fail(str(exc))
        _print_payload(status.to_dict(), output_format=output_format, title="Workspace schema")
        if status.layout_status in {LAYOUT_INVALID, LAYOUT_UNSUPPORTED, LAYOUT_AHEAD}:
            raise typer.Exit(code=1)

    @migrate_app.command("plan")
    def migrate_plan(
        target_version: int = typer.Option(1, "--to", help="Target workspace schema version"),
        input_patch: Path | None = typer.Option(None, "--input", help="Owner input YAML patch"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Build a deterministic migration plan without writing workspace state."""
        try:
            owner_inputs = load_owner_input_patch(input_patch) if input_patch else {}
            plan = workspace_for(root).workspace_migration_plan(target_version, owner_inputs)
        except ValueError as exc:
            fail(str(exc))
        _print_payload(plan.to_dict(), output_format=output_format, title="Workspace migration plan")
        if any(item.classification in {"invalid", "unsupported"} for item in plan.findings):
            raise typer.Exit(code=1)

    @migrate_app.command("attestation-template")
    def migration_attestation_template(
        target_version: int = typer.Option(
            3,
            "--to",
            help="Target workspace schema version",
        ),
        owner: str = typer.Option(
            ...,
            "--owner",
            help="Current declared owner reviewing legacy decisions",
        ),
        output_format: str = typer.Option(
            "text",
            "--format",
            help="Output format: text or json",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a read-only, source-bound legacy authority input template."""
        try:
            template = workspace_for(
                root
            ).workspace_migration_attestation_template(
                target_version=target_version,
                owner_id=owner,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_payload(
            template.to_dict(),
            output_format=output_format,
            title="Workspace migration attestation template",
        )

    @migrate_app.command("apply")
    def migrate_apply(
        target_version: int = typer.Option(..., "--to", help="Target workspace schema version"),
        input_patch: Path | None = typer.Option(None, "--input", help="Reviewed owner input YAML patch"),
        plan_fingerprint: str = typer.Option(..., "--plan-fingerprint", help="Reviewed semantic plan fingerprint"),
        actor: str = typer.Option(..., "--actor", help="Authorized owner actor"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm migration apply"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Apply a reviewed workspace migration transaction."""
        try:
            owner_inputs = load_owner_input_patch(input_patch) if input_patch else {}
            result = workspace_for(root).workspace_migration_apply(
                target_version=target_version,
                owner_inputs=owner_inputs,
                plan_fingerprint=plan_fingerprint,
                actor=actor,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_payload(result.to_dict(), output_format=output_format, title="Workspace migration apply")
        if result.status not in {MIGRATION_STATUS_APPLIED, MIGRATION_STATUS_NO_OP}:
            raise typer.Exit(code=1)

    @recovery_app.command("status")
    def recovery_status(
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Inspect interrupted workspace migration recovery state."""
        result = workspace_for(root).workspace_migration_recovery_status()
        _print_payload(result.to_dict(), output_format=output_format, title="Workspace migration recovery")

    @recovery_app.command("rollback")
    def recovery_rollback(
        transaction_id: str = typer.Option(..., "--transaction-id", help="Recovery transaction id"),
        actor: str = typer.Option(..., "--actor", help="Authorized owner actor"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm recovery rollback"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Rollback an interrupted workspace migration."""
        result = workspace_for(root).workspace_migration_rollback(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )
        _print_payload(result.to_dict(), output_format=output_format, title="Workspace migration rollback")
        if result.status not in {"rolled_back", MIGRATION_STATUS_NO_OP}:
            raise typer.Exit(code=1)

    @recovery_app.command("resume")
    def recovery_resume(
        transaction_id: str = typer.Option(..., "--transaction-id", help="Recovery transaction id"),
        actor: str = typer.Option(..., "--actor", help="Authorized owner actor"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm recovery resume"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Resume an interrupted workspace migration when exact preconditions hold."""
        result = workspace_for(root).workspace_migration_resume(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )
        _print_payload(result.to_dict(), output_format=output_format, title="Workspace migration resume")
        if result.status not in {MIGRATION_STATUS_APPLIED, MIGRATION_STATUS_NO_OP}:
            raise typer.Exit(code=1)


def _print_payload(payload: dict[str, object], *, output_format: str, title: str) -> None:
    if output_format == "json":
        console.out(json.dumps(payload, indent=2), highlight=False)
        return
    if output_format != "text":
        fail("Workspace migration format must be text or json")
    console.print(title)
    for key in (
        "state",
        "status",
        "layout_status",
        "alignment_status",
        "current_version",
        "source_version",
        "target_version",
        "applicable",
        "fingerprint_sha256",
        "source_plan_fingerprint_sha256",
        "transaction_id",
        "required",
        "journal_state",
        "message",
        "included_count",
        "manual_review_count",
    ):
        if key in payload and payload[key] not in (None, ""):
            console.print(f"  {key}: {payload[key]}")
    operations = payload.get("operations")
    if isinstance(operations, list) and operations:
        console.print("Operations:")
        for operation in operations:
            if isinstance(operation, dict):
                console.print(
                    f"  {operation.get('operation_id')} {operation.get('kind')} {operation.get('target')}"
                )
    findings = payload.get("findings")
    if isinstance(findings, list) and findings:
        console.print("Findings:")
        for finding in findings:
            if isinstance(finding, dict):
                classification = finding.get("classification") or finding.get("severity")
                console.print(f"  {classification} {finding.get('code')} {finding.get('path') or ''}".rstrip())
                console.print(f"    {finding.get('message')}")
    manual_review = payload.get("manual_review")
    if isinstance(manual_review, list) and manual_review:
        console.print("Manual review:")
        for item in manual_review:
            if isinstance(item, dict):
                console.print(
                    f"  {item.get('proposal_id')} {item.get('legacy_status')} "
                    f"{item.get('reason')}"
                )
    for key in ("changed_paths", "restored_paths"):
        paths = payload.get(key)
        if isinstance(paths, list) and paths:
            console.print(f"{key}:")
            for path in paths:
                console.print(f"  - {path}")
