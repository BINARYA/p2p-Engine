from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

import typer

from p2p_engine.cli_contract import print_json
from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for


_P2P_OPERATION_KEY = re.compile(r"^P2POP-[0-9a-f]{24}$")


def register_mutation_commands(mutation_app: typer.Typer) -> None:
    @mutation_app.command("status")
    def mutation_status(
        idempotency_key: str = typer.Option(
            ...,
            "--idempotency-key",
            "--operation-key",
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
        payload["operation_key"] = {
            "classification": _operation_key_classification(idempotency_key),
            "raw_value_returned": False,
        }
        if output_format == "json":
            print_json(payload)
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


def _operation_key_classification(value: str) -> str:
    if value.startswith("wavekit:"):
        try:
            UUID(value.partition(":")[2])
        except ValueError:
            return "wavekit_opaque"
        return "wavekit_uuid"
    if _P2P_OPERATION_KEY.fullmatch(value):
        return "p2p_operation"
    return "opaque"
