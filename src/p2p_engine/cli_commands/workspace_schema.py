from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.workspace_schema import LAYOUT_CURRENT


def register_workspace_schema_commands(schema_app: typer.Typer) -> None:
    @schema_app.command("status")
    def schema_status(
        output_format: str = typer.Option(
            "text",
            "--format",
            help="Output format: text or json",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show the read-only current workspace-schema status."""
        try:
            status = workspace_for(root).workspace_schema_status()
        except ValueError as exc:
            fail(str(exc))
        payload = status.to_dict()
        if output_format == "json":
            print_json(payload)
        elif output_format == "text":
            console.print("Workspace schema")
            for key in (
                "state",
                "layout_status",
                "alignment_status",
                "current_version",
                "target_version",
            ):
                console.print(f"  {key}: {payload[key]}")
            for finding in payload["findings"]:
                console.print(
                    f"  {finding['severity']} {finding['code']}: {finding['message']}"
                )
        else:
            fail("Workspace schema format must be text or json")
        if status.layout_status != LAYOUT_CURRENT:
            raise typer.Exit(code=1)
