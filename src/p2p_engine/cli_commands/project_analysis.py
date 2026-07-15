from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.services.proposal_artifacts import load_impact_artifacts


def register_project_analysis_commands(
    impact_app: typer.Typer,
    conflict_app: typer.Typer,
) -> None:
    @impact_app.command("prompt")
    def impact_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate an impact-analysis prompt file."""
        try:
            path = workspace_for(root).generate_prompt(proposal_id, "impact")
        except ValueError as exc:
            fail(str(exc))
        console.print(f"[green]Generated[/green] {path}")

    @impact_app.command("import")
    def impact_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Impact output file or artifact directory"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import impact artifacts into a proposal."""
        try:
            imported = workspace_for(root).import_impact(proposal_id, source)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Impact imported.[/green]")
        for path in imported:
            console.print(f"  updated {path}")

    @impact_app.command("preview")
    def impact_preview(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Complete impact artifact file or directory"),
        actor: str = typer.Option(..., "--actor", help="Actor requesting correction"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview a complete impact correction without writing proposal state."""
        try:
            preview = workspace_for(root).preview_proposal_impact(
                proposal_id,
                load_impact_artifacts(source),
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_mutation(preview.to_dict(), output_format, "Impact correction preview")

    @impact_app.command("apply")
    def impact_apply(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Complete impact artifact file or directory"),
        preview_token: str = typer.Option(..., "--preview-token", help="Token returned by preview"),
        actor: str = typer.Option(..., "--actor", help="Authorized actor"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm impact correction"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Apply a stale-preview-protected impact correction."""
        try:
            result = workspace_for(root).apply_proposal_impact(
                proposal_id,
                load_impact_artifacts(source),
                preview_token=preview_token,
                actor=actor,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_mutation(result.to_dict(), output_format, "Impact correction apply")
        if result.status != "applied":
            raise typer.Exit(code=1)

    @conflict_app.command("record")
    def conflict_record(
        proposal_ids: list[str] = typer.Argument(..., help="Two or more proposal IDs"),
        conflict_type: str = typer.Option("overlaps", "--type", help="Conflict relationship type"),
        reason: str = typer.Option(..., "--reason", help="Why these proposals conflict or overlap"),
        winner: str | None = typer.Option(None, "--winner", help="Winning proposal if decided"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Record conflict memory in .p2p/project/conflicts.yml."""
        try:
            status = workspace_for(root).record_conflict(
                proposals=proposal_ids,
                conflict_type=conflict_type,
                reason=reason,
                winner=winner,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Conflict recorded.[/green]")
        console.print(f"  conflicts: {status.conflicts_count}")
        console.print(f"  file: {status.conflicts_file}")

    @conflict_app.command("status")
    def conflict_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show recorded project conflicts."""
        try:
            status = workspace_for(root).conflict_status()
        except ValueError as exc:
            fail(str(exc))
        console.print("Project conflicts")
        console.print(f"  file: {status.conflicts_file}")
        if not status.conflicts:
            console.print("  conflicts: none")
            return
        for conflict in status.conflicts:
            proposals = ", ".join(str(item) for item in conflict.get("proposals", []))
            console.print(f"  {conflict.get('id')}: {conflict.get('type')} [{proposals}]")

    @conflict_app.command("show")
    def conflict_show(
        conflict_id: str = typer.Argument(..., help="Conflict ID"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show one stable conflict-memory record."""
        try:
            conflict = workspace_for(root).conflict_show(conflict_id)
        except ValueError as exc:
            fail(str(exc))
        _print_mutation(conflict, output_format, "Project conflict")

    @conflict_app.command("preview-update")
    def conflict_preview_update(
        conflict_id: str = typer.Argument(..., help="Conflict ID"),
        patch: Path = typer.Argument(..., help="Structured conflict patch YAML"),
        actor: str = typer.Option(..., "--actor", help="Actor requesting correction"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview an update to one existing conflict id."""
        try:
            preview = workspace_for(root).preview_conflict_update(
                conflict_id,
                _yaml_mapping(patch),
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_mutation(preview.to_dict(), output_format, "Conflict update preview")

    @conflict_app.command("update")
    def conflict_update(
        conflict_id: str = typer.Argument(..., help="Conflict ID"),
        patch: Path = typer.Argument(..., help="Structured conflict patch YAML"),
        preview_token: str = typer.Option(..., "--preview-token", help="Token returned by preview"),
        actor: str = typer.Option(..., "--actor", help="Authorized owner actor"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm conflict correction"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Apply an update to one existing conflict id."""
        try:
            result = workspace_for(root).update_conflict(
                conflict_id,
                _yaml_mapping(patch),
                preview_token=preview_token,
                actor=actor,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_mutation(result.to_dict(), output_format, "Conflict update apply")
        if result.status != "applied":
            raise typer.Exit(code=1)


def _yaml_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"Patch file not found: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML patch: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Patch must contain a YAML mapping.")
    return payload


def _print_mutation(payload: dict[str, object], output_format: str, title: str) -> None:
    if output_format == "json":
        console.out(json.dumps(payload, indent=2), highlight=False)
        return
    if output_format != "text":
        fail("Analysis mutation format must be text or json")
    console.print(title)
    for key in ("id", "status", "operation_id", "authority", "apply_allowed", "preview_token", "message"):
        if key in payload and payload[key] not in (None, ""):
            console.print(f"  {key}: {payload[key]}")
    paths = payload.get("changed_paths")
    if isinstance(paths, list):
        for path in paths:
            console.print(f"  changed: {path}")
