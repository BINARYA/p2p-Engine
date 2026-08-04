from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console

from p2p_engine.cli_contract import contract_failure, json_mode_active
from p2p_engine.storage.filesystem import P2PWorkspace


console = Console()


def fail(message: str) -> None:
    if json_mode_active():
        contract_failure(message)
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)


def workspace(root: Path) -> P2PWorkspace:
    return P2PWorkspace(root)


def yaml_dump_for_cli(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
