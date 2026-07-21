from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_registry_commands(registry_app: typer.Typer) -> None:
    @registry_app.command("refresh")
    def registry_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Regenerate typed project registries from P2P source artifacts."""
        try:
            written = workspace_for(root).refresh_registries()
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Registries refreshed.[/green]")
        for path in written:
            console.print(f"  updated {path}")

    @registry_app.command("status")
    def registry_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show generated registry availability and basic freshness checks."""
        try:
            status = workspace_for(root).registry_status()
        except ValueError as exc:
            fail(str(exc))
        console.print("Registry status")
        console.print(f"  path: {status.registries_dir}")
        console.print(f"  source proposals: {status.proposals_count}")
        console.print(f"  source changes: {status.changes_count}")
        console.print(f"  stale: {status.stale}")
        console.print(f"  state: {status.state}")
        console.print(f"  reason: {status.reason}")
        if status.manifest_version is not None:
            console.print(f"  manifest version: {status.manifest_version}")
            console.print(f"  source fingerprint: {status.source_fingerprint_sha256}")
        console.print("  files:")
        for file in status.files:
            marker = "✓" if file["exists"] and file["generated"] else "✗"
            console.print(f"    {marker} {file['name']} ({file['records']} records)")

    @registry_app.command("show")
    def registry_show(
        name: str = typer.Argument(
            ...,
            help="Registry name: proposals, decisions, changes, choices, relations, artifacts, readiness",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a generated registry."""
        try:
            view = workspace_for(root).show_registry(name)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"Registry: [bold]{view.name}[/bold]")
        console.print(f"  path: {view.path}")
        if not view.records:
            console.print("  records: none")
            return
        for record in view.records:
            if view.name in {"proposals", "changes"}:
                console.print(
                    f"  {record.get('id', '-')}: {record.get('status', 'unknown')}  {record.get('title', '')}"
                )
            elif view.name == "decisions":
                console.print(
                    f"  {record.get('proposal', '-')}: {record.get('outcome', 'unknown')}  {record.get('title', '')}"
                )
            elif view.name == "relations":
                console.print(
                    f"  {record.get('source', '-')} -> {record.get('target', '-')}  {record.get('type', '')}"
                )
            elif view.name == "choices":
                selected = f" -> {record.get('selected_option')}" if record.get("selected_option") else ""
                title = record.get("title") or record.get("proposal", "")
                console.print(f"  {record.get('id', '-')}: {record.get('status', 'unknown')}  {title}{selected}")
            elif view.name == "artifacts":
                console.print(
                    f"  {record.get('owner_type', '-')}/{record.get('owner', '-')}: {record.get('path', '')}"
                )
            elif view.name == "readiness":
                score = record.get("computed_score")
                score_text = str(score) if score is not None else "none"
                console.print(
                    f"  {record.get('proposal', '-')}: {record.get('status', 'unknown')}  "
                    f"{score_text} {record.get('computed_label') or 'none'}"
                )
            else:
                console.print(f"  {record}")
