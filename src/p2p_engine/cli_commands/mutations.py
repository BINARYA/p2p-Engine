from __future__ import annotations

import json
from pathlib import Path

import typer

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_mutation_commands(mutation_app: typer.Typer) -> None:
    @mutation_app.command("status")
    def mutation_status(
        idempotency_key: str = typer.Option(
            ...,
            "--idempotency-key",
            help="Opaque caller-supplied mutation idempotency key",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Inspect a durable mutation receipt without changing project state."""
        try:
            result = workspace_for(root).mutation_status(idempotency_key=idempotency_key)
        except ValueError as exc:
            fail(str(exc))
        payload = result.to_dict()
        if output_format == "json":
            console.out(json.dumps(payload, indent=2), highlight=False)
            return
        if output_format != "text":
            fail("Mutation status format must be text or json")
        for key, value in payload.items():
            if key != "result":
                console.print(f"{key}: {value}")
        if payload["result"]:
            console.print("result:")
            for key, value in payload["result"].items():
                console.print(f"  {key}: {value}")
