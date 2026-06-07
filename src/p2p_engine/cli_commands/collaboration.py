from __future__ import annotations

import typer

from p2p_engine.cli_commands.choices import register_choice_commands
from p2p_engine.cli_commands.governance import register_governance_commands
from p2p_engine.cli_commands.intake import register_intake_commands
from p2p_engine.cli_commands.project_analysis import register_project_analysis_commands
from p2p_engine.cli_commands.registry import register_registry_commands


def register_collaboration_commands(
    governance_app: typer.Typer,
    vote_app: typer.Typer,
    precedent_app: typer.Typer,
    impact_app: typer.Typer,
    conflict_app: typer.Typer,
    registry_app: typer.Typer,
    intake_app: typer.Typer,
    intake_apply_app: typer.Typer,
    choice_app: typer.Typer,
) -> None:
    register_governance_commands(governance_app, vote_app, precedent_app)
    register_project_analysis_commands(impact_app, conflict_app)
    register_registry_commands(registry_app)
    register_intake_commands(intake_app, intake_apply_app)
    register_choice_commands(choice_app)
