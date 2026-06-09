from __future__ import annotations

import typer

from p2p_engine.cli_commands.proposal_branches import register_proposal_branch_commands
from p2p_engine.cli_commands.proposal_artifact_state import register_proposal_artifact_commands
from p2p_engine.cli_commands.proposal_contributions import register_proposal_contribution_commands
from p2p_engine.cli_commands.proposal_core import register_proposal_core_commands
from p2p_engine.cli_commands.proposal_decisions import register_proposal_decision_commands
from p2p_engine.cli_commands.proposal_questions import register_proposal_question_commands
from p2p_engine.cli_commands.proposal_readiness import register_proposal_readiness_commands


def register_proposal_commands(
    proposal_app: typer.Typer,
    proposal_readiness_app: typer.Typer,
    proposal_questions_app: typer.Typer,
    proposal_artifact_app: typer.Typer,
    proposal_contribution_app: typer.Typer,
    contribution_app: typer.Typer,
    decision_app: typer.Typer,
) -> None:
    register_proposal_core_commands(proposal_app)
    register_proposal_readiness_commands(proposal_readiness_app)
    register_proposal_question_commands(proposal_questions_app)
    register_proposal_artifact_commands(proposal_artifact_app)
    register_proposal_branch_commands(proposal_app)
    register_proposal_decision_commands(proposal_app, decision_app)
    register_proposal_contribution_commands(proposal_app, proposal_contribution_app, contribution_app)
