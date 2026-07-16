from __future__ import annotations

from p2p_engine.prompts.common import (
    render_governance_context,
    render_missing_info_instruction,
    render_nearby_decision_context,
)


def render_explore_prompt(context: dict[str, str]) -> str:
    return (
        f"# P2P Exploration Prompt - {context['proposal_id']}\n\n"
        "You are assisting P2P Engine during the Exploration Phase.\n\n"
        "Your task is not to summarize and not to decide. Your task is to interrogate a rough idea "
        "and surface implications before the proposal is synthesized.\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "## Required Output Files\n\n"
        "Produce content suitable for these P2P artifacts:\n\n"
        "- exploration.md\n"
        "- findings.md\n"
        "- alternatives.md\n"
        "- open-questions.md\n"
        "- risks.md\n"
        "- assumptions.md\n"
        "- suggested-scope.md\n\n"
        "## What To Discover\n\n"
        "- hidden decisions\n"
        "- architectural implications\n"
        "- alternative approaches\n"
        "- assumptions\n"
        "- risks and mitigations\n"
        "- unclear scope boundaries\n"
        "- missing requirements\n"
        "- possible execution domains\n"
        "- questions that should be answered before synthesis\n\n"
        "## Findings Format\n\n"
        "For `findings.md`, include structured findings like:\n\n"
        "```yaml\n"
        "findings:\n"
        "  - id: F001\n"
        "    type: hidden_decision\n"
        "    title: AI integration strategy\n"
        "    impact: high\n"
        "    related_to:\n"
        "      - PROP-001\n"
        "```\n\n"
        "## Proposal\n\n"
        f"{context['proposal']}\n\n"
        "## Contributions\n\n"
        f"{context['contributions']}\n\n"
        "## Comments\n\n"
        f"{context['comments']}\n\n"
        f"{render_nearby_decision_context(context)}\n\n"
        f"{render_governance_context(context)}\n"
    )
