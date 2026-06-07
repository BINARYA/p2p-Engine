from __future__ import annotations

from p2p_engine.mcp.catalog.common import schema as _schema


PROMPT_TOOL_KINDS = {
    "p2p_explore_prompt": "explore",
    "p2p_digest_prompt": "digest",
    "p2p_clarify_prompt": "clarify",
    "p2p_synthesize_prompt": "synthesize",
    "p2p_plan_prompt": "plan",
    "p2p_tasks_prompt": "tasks",
    "p2p_swot_prompt": "swot",
}


def tool_definitions() -> list[dict[str, object]]:
    definitions = []
    for tool_name, kind in PROMPT_TOOL_KINDS.items():
        definitions.append(
            {
                "name": tool_name,
                "description": (
                    f"Advisory prompt tool: generate a {kind} prompt for an existing "
                    "proposal. Does not import output or change decisions."
                ),
                "inputSchema": _schema(
                    {"root": {"type": "string"}, "proposal_id": {"type": "string"}},
                    ["proposal_id"],
                ),
            }
        )
    definitions.append(
        {
            "name": "p2p_spec_prompt",
            "description": (
                "Advisory prompt tool: generate a software-spec refinement prompt for "
                "a Change Set. Does not import output or change decisions."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "change_id": {"type": "string"}},
                ["change_id"],
            ),
        }
    )
    return definitions
