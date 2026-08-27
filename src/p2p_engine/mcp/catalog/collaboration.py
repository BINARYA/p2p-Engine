from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _decision_tool("accept", "acceptance"),
        _decision_tool("reject", "rejection"),
        _decision_tool("defer", "deferral"),
    ]


def _decision_tool(action: str, noun: str) -> dict[str, object]:
    return _tool(
        f"p2p_proposal_{action}",
        (
            f"Convenience tool for a proposal {noun}: return the same token-bound "
            "preview used by the current decision-event workflow. Apply through "
            "p2p_proposal_decision_apply with preview-bound consent."
        ),
        {
            "root": {"type": "string"},
            "proposal_id": {"type": "string"},
            "actor_id": {"type": "string"},
            "owner_id": {"type": "string"},
            "consent_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        ["proposal_id", "actor_id", "consent_id", "reason"],
    )
