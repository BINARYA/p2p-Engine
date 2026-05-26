from __future__ import annotations

from p2p_engine.prompts.common import render_governance_context, render_missing_info_instruction


def render_swot_prompt(context: dict[str, str]) -> str:
    proposal_id = context["proposal_id"]
    return (
        f"# P2P SWOT Prompt - {proposal_id}\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "You are supporting the P2P governance phase. Produce a SWOT analysis that helps "
        "humans compare competing alternatives before a governance decision. Do not decide "
        "the winner unless the governance artifacts explicitly say that a decision has "
        "already been made.\n\n"
        "## Required Output\n\n"
        "Write Markdown suitable for `swot-analysis.md` with these sections:\n\n"
        f"1. `# SWOT Analysis - {proposal_id}`\n"
        "2. `## Alternatives Considered`\n"
        "3. For each alternative: `Strengths`, `Weaknesses`, `Opportunities`, `Threats`\n"
        "4. `## Decision-Relevant Trade-offs`\n"
        "5. `## Missing Information`\n"
        "6. `## Suggested Governance Next Step`\n\n"
        "## Proposal\n\n"
        f"{context.get('proposal', '').strip() or 'Not provided.'}\n\n"
        "## Alternatives\n\n"
        f"{context.get('alternatives', '').strip() or 'Not provided.'}\n\n"
        "## Exploration Findings\n\n"
        f"{context.get('findings', '').strip() or 'Not provided.'}\n\n"
        "## Risks\n\n"
        f"{context.get('risks', '').strip() or 'Not provided.'}\n\n"
        "## Assumptions\n\n"
        f"{context.get('assumptions', '').strip() or 'Not provided.'}\n\n"
        "## Existing Votes\n\n"
        f"{context.get('votes', '').strip() or 'Not provided.'}\n\n"
        "## Governance Files\n\n"
        "### governance.yml\n\n"
        f"{context.get('governance', '').strip() or 'Not provided.'}\n\n"
        "### roles.yml\n\n"
        f"{context.get('roles', '').strip() or 'Not provided.'}\n\n"
        "### decision-precedents.yml\n\n"
        f"{context.get('decision_precedents', '').strip() or 'Not provided.'}\n\n"
        f"{render_governance_context(context)}\n"
    )
