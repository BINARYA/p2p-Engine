from __future__ import annotations

from p2p_engine.prompts.common import render_governance_context, render_missing_info_instruction


def render_clarify_prompt(context: dict[str, str]) -> str:
    return (
        f"# P2P Clarify Prompt - {context['proposal_id']}\n\n"
        "Generate focused clarification questions for this proposal. Do not answer them yourself.\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "## Required Output\n\n"
        "Return 5-10 numbered questions grouped by theme.\n\n"
        "## Proposal\n\n"
        f"{context['proposal']}\n\n"
        "## Contributions\n\n"
        f"{context['contributions']}\n\n"
        f"{render_governance_context(context)}\n"
    )
