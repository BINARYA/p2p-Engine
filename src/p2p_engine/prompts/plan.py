from __future__ import annotations

from p2p_engine.prompts.common import render_governance_context, render_missing_info_instruction


def render_plan_prompt(context: dict[str, str]) -> str:
    return (
        f"# P2P Plan Prompt - {context['proposal_id']}\n\n"
        "Create an execution plan for the accepted proposal.\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "## Required Output Sections\n\n"
        "- Objective\n"
        "- Workstreams\n"
        "- Milestones\n"
        "- Dependencies\n"
        "- Risks\n"
        "- Next step\n\n"
        "## Proposal\n\n"
        f"{context['proposal']}\n\n"
        "## Clarifications\n\n"
        f"{context['clarifications']}\n\n"
        "## Decision\n\n"
        f"{context['decision']}\n\n"
        f"{render_governance_context(context)}\n"
    )
