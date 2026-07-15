from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

import typer

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.cli_commands.formatting import emit_structured
from p2p_engine.foundation.files import read_yaml_mapping


def register_proposal_vertical_coverage_commands(app: typer.Typer) -> None:
    @app.command("show")
    def show(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show declared vertical coverage status."""
        try:
            status = workspace_for(root).proposal_vertical_coverage_status(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        _print(status, output_format, "Vertical coverage")

    @app.command("suggest")
    def suggest(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Suggest section mappings without creating authoritative state."""
        try:
            suggestion = workspace_for(root).suggest_proposal_vertical_coverage(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        _print(suggestion, output_format, "Vertical coverage suggestion")

    @app.command("preview")
    def preview(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Complete coverage YAML payload"),
        actor: str = typer.Option(..., "--actor", help="Owner identity reviewing the mapping"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview coverage and artifact-state replacement without writing."""
        try:
            payload = read_yaml_mapping(source, default={})
            result = workspace_for(root).preview_proposal_vertical_coverage(proposal_id, payload, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        _print(result, output_format, "Vertical coverage import preview")

    @app.command("import")
    def import_coverage(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Complete coverage YAML supplied again"),
        preview_token: str = typer.Option(..., "--preview-token", help="Token returned by preview"),
        actor: str = typer.Option(..., "--actor", help="Owner identity applying the mapping"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the reviewed mapping"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Atomically import vertical coverage and its artifact-state provenance."""
        try:
            payload = read_yaml_mapping(source, default={})
            result = workspace_for(root).apply_proposal_vertical_coverage(
                proposal_id,
                payload,
                preview_token=preview_token,
                actor=actor,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        _print(result, output_format, "Vertical coverage import")
        if result.status != "applied":
            raise typer.Exit(code=1)


def _print(value: object, output_format: str, title: str) -> None:
    if output_format.strip().lower() == "json":
        emit_structured(value, "json")
        return
    payload = value.to_dict() if hasattr(value, "to_dict") else asdict(value) if is_dataclass(value) else value
    console.print(title)
    if isinstance(payload, dict):
        for key in ("proposal_id", "vertical_id", "state", "status", "authority", "preview_token", "message"):
            if key in payload and payload[key] not in (None, "", []):
                console.print(f"  {key}: {payload[key]}")
        candidates = payload.get("candidates")
        if isinstance(candidates, list):
            console.print(f"  candidates: {len(candidates)}")
