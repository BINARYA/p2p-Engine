from __future__ import annotations

from p2p_engine.prompts.common import render_governance_context, render_missing_info_instruction


def render_digest_prompt(context: dict[str, str]) -> str:
    return _render("digest", context)


def _render(kind: str, context: dict[str, str]) -> str:
    return (
        f"# P2P {kind.title()} Prompt - {context['proposal_id']}\n\n"
        "You are assisting P2P Engine. Produce a structured digest without making a decision.\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "## Required Output Sections\n\n"
        "- Summary\n"
        "- Main objectives\n"
        "- Key constraints\n"
        "- Risks\n"
        "- Conflicts\n"
        "- Open questions\n"
        "- Suggested next steps\n\n"
        "## Proposal\n\n"
        f"{context['proposal']}\n\n"
        "## Contributions\n\n"
        f"{context['contributions']}\n\n"
        "## Comments\n\n"
        f"{context['comments']}\n\n"
        f"{render_governance_context(context)}\n"
    )
