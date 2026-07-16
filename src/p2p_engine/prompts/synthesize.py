from __future__ import annotations

from p2p_engine.prompts.common import (
    render_governance_context,
    render_missing_info_instruction,
    render_nearby_decision_context,
)


def render_synthesize_prompt(context: dict[str, str]) -> str:
    return (
        f"# P2P Synthesize Prompt - {context['proposal_id']}\n\n"
        "Transform the available P2P artifacts into a structured proposal ready for review.\n\n"
        "Do not record a final decision. Keep the decision section pending unless an explicit "
        "human decision artifact already exists.\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "## Required Output\n\n"
        "Return a complete `proposal.md` with these sections:\n\n"
        "- Status\n"
        "- Problem\n"
        "- Context\n"
        "- Goals\n"
        "- Non-Goals\n"
        "- Proposal\n"
        "- Alternatives\n"
        "- Impacts\n"
        "- Risks\n"
        "- Open Questions\n"
        "- Acceptance Criteria\n"
        "- Decision\n\n"
        "## Current Proposal\n\n"
        f"{context['proposal']}\n\n"
        "## Exploration\n\n"
        f"{context['exploration']}\n\n"
        "## Findings\n\n"
        f"{context['findings']}\n\n"
        "## Alternatives\n\n"
        f"{context['alternatives']}\n\n"
        "## Open Questions\n\n"
        f"{context['open_questions']}\n\n"
        "## Risks\n\n"
        f"{context['risks']}\n\n"
        "## Assumptions\n\n"
        f"{context['assumptions']}\n\n"
        "## Suggested Scope\n\n"
        f"{context['suggested_scope']}\n\n"
        "## Contributions\n\n"
        f"{context['contributions']}\n\n"
        "## Comments\n\n"
        f"{context['comments']}\n\n"
        "## Clarifications\n\n"
        f"{context['clarifications']}\n\n"
        f"{render_nearby_decision_context(context)}\n\n"
        f"{render_governance_context(context)}\n"
    )
