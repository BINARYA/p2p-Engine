from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console

try:  # Typer 0.27 vendors Click; older supported Typer versions do not.
    from typer._click.globals import get_current_context
except ImportError:  # pragma: no cover - exercised by older dependency sets.
    from click import get_current_context  # type: ignore[no-redef]

from p2p_engine.cli_contract import (
    contract_failure,
    json_mode_active,
    set_linked_freshness,
)
from p2p_engine.services.project_application import (
    ProjectApplicationService,
    open_project_application,
)

console = Console()


def fail(message: str) -> None:
    if json_mode_active():
        contract_failure(message)
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)


def workspace(root: Path) -> ProjectApplicationService:
    application = open_project_application(root)
    if _linked_preflight_required():
        try:
            freshness = application.linked_replica_before_operation(mutation=False)
        except ValueError as exc:
            fail(str(exc))
        set_linked_freshness(freshness)
        if (
            freshness is not None
            and bool(getattr(freshness, "stale", False))
            and not json_mode_active()
        ):
            console.print(
                "[yellow]Warning:[/yellow] WaveKit could not be verified; "
                "this command is using the last confirmed local replica state."
            )
    return application


def _linked_preflight_required() -> bool:
    """Keep recovery/bootstrap commands outside the normal one-shot preflight."""
    context = get_current_context(silent=True)
    names: list[str] = []
    while context is not None:
        if context.info_name:
            names.append(str(context.info_name))
        context = context.parent
    path = tuple(reversed(names))
    # The first element is the executable name chosen by the caller/test.
    command = path[1:]
    if not command:
        return False
    if command[0] in {"auth", "wavekit", "sync", "integration"}:
        return False
    if command[:2] in {("project", "replication"), ("project", "transfer")}:
        return False
    return True


def yaml_dump_for_cli(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
