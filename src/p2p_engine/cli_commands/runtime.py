from __future__ import annotations

import json
from pathlib import Path

import typer

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_runtime_commands(runtime_app: typer.Typer) -> None:
    @runtime_app.command("status")
    def status(
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show read-only P2P Engine runtime compatibility status."""
        try:
            runtime_status = workspace_for(root).runtime_status()
        except ValueError as exc:
            fail(str(exc))
        if output_format == "json":
            console.print(json.dumps(runtime_status.to_dict(), indent=2))
        elif output_format == "text":
            console.print("Runtime")
            console.print(f"  state: {runtime_status.state}")
            console.print(f"  contract: {runtime_status.contract_path}")
            console.print(f"  current_version: {runtime_status.current_version or 'unknown'}")
            console.print(f"  requires: {runtime_status.requires or 'none'}")
            console.print(f"  recommended: {runtime_status.recommended or 'none'}")
            console.print(f"  compatible: {str(runtime_status.compatible).lower()}")
            if runtime_status.findings:
                console.print("Findings:")
                for finding in runtime_status.findings:
                    console.print(f"  {finding.severity.upper()} {finding.code} {finding.path}")
                    console.print(f"    {finding.message}")
                    if finding.suggested_command:
                        console.print(f"    command: {finding.suggested_command}")
        else:
            fail("Runtime status format must be text or json")
