from __future__ import annotations

import typer

from p2p_engine.cli_commands.changes import register_change_commands
from p2p_engine.cli_commands.specs import register_spec_commands
from p2p_engine.cli_commands.work import register_work_commands


def register_work_spec_commands(
    change_app: typer.Typer,
    spec_app: typer.Typer,
    work_app: typer.Typer,
) -> None:
    register_change_commands(change_app)
    register_spec_commands(spec_app)
    register_work_commands(work_app)
