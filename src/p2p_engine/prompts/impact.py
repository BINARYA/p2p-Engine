from __future__ import annotations

from p2p_engine.prompts.common import (
    render_governance_context,
    render_missing_info_instruction,
    render_nearby_decision_context,
)


def render_impact_prompt(context: dict[str, str]) -> str:
    proposal_id = context["proposal_id"]
    return (
        f"# P2P Impact Prompt - {proposal_id}\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "Analyze what this proposal touches and whether it overlaps, depends on, "
        "supersedes, duplicates, or conflicts with existing project state and proposals. "
        "Do not decide the proposal outcome.\n\n"
        "## Required Output\n\n"
        "Return three YAML documents or files:\n\n"
        "1. `impact-map.yml` with top-level key `impact`\n"
        "2. `related-proposals.yml` with top-level key `related_proposals`\n"
        "3. `conflict-analysis.yml` with top-level key `conflicts`\n\n"
        "## impact-map.yml Shape\n\n"
        "```yaml\n"
        "impact:\n"
        f"  proposal: {proposal_id}\n"
        "  features: []\n"
        "  commands: []\n"
        "  files: []\n"
        "  governance: []\n"
        "  project_artifacts: []\n"
        "  dependencies: []\n"
        "  risks: []\n"
        "```\n\n"
        "## related-proposals.yml Shape\n\n"
        "```yaml\n"
        "related_proposals:\n"
        "  - proposal: PROP-000\n"
        "    relationship: references\n"
        "    reason: Example reason\n"
        "```\n\n"
        "## conflict-analysis.yml Shape\n\n"
        "```yaml\n"
        "conflicts:\n"
        "  - type: mutually_exclusive\n"
        "    proposals:\n"
        f"      - {proposal_id}\n"
        "    reason: Example reason\n"
        "    suggested_resolution: human_decision_required\n"
        "```\n\n"
        "## Proposal\n\n"
        f"{context.get('proposal', '').strip() or 'Not provided.'}\n\n"
        "## Contributions\n\n"
        f"{context.get('contributions', '').strip() or 'Not provided.'}\n\n"
        "## Exploration\n\n"
        f"{context.get('exploration', '').strip() or 'Not provided.'}\n\n"
        "## Existing Project Decisions\n\n"
        "The following bounded neighborhood replaces registry-order and full decision-map context.\n\n"
        f"{render_nearby_decision_context(context)}\n\n"
        "## Project Overview\n\n"
        f"{context.get('project_overview', '').strip() or 'Not provided.'}\n\n"
        f"{render_governance_context(context)}\n"
    )
