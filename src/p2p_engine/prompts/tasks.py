from __future__ import annotations

from p2p_engine.prompts.common import render_governance_context, render_missing_info_instruction


def render_tasks_prompt(context: dict[str, str]) -> str:
    return (
        f"# P2P Tasks Prompt - {context['proposal_id']}\n\n"
        "Generate implementation tasks and actions as YAML. Keep tasks specific and verifiable.\n\n"
        f"{render_missing_info_instruction()}\n\n"
        "## Required YAML Shape\n\n"
        "```yaml\n"
        "tasks:\n"
        "  - id: T001\n"
        "    title: Example task\n"
        "    workstream: WS1\n"
        "    type: software\n"
        "    status: todo\n"
        "    priority: high\n"
        "    dependencies: []\n"
        "    deliverable: Example deliverable\n"
        "    evidence_required: Example evidence\n"
        "    actions:\n"
        "      - id: A001\n"
        "        title: Example action\n"
        "        status: todo\n"
        "```\n\n"
        "## Proposal\n\n"
        f"{context['proposal']}\n\n"
        "## Decision\n\n"
        f"{context['decision']}\n\n"
        f"{render_governance_context(context)}\n"
    )
