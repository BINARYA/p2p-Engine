from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    page = {
        "root": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "cursor": {"type": "string"},
    }
    return [
        _tool(
            "p2p_project_readiness_review",
            "Read a bounded advisory project-readiness review; never mutates project state.",
            {
                "root": {"type": "string"},
                "vertical_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        ),
        _tool(
            "p2p_project_readiness_gaps",
            "List prioritized project-readiness gaps with snapshot-bound pagination.",
            {
                **page,
                "kind": {"type": "string"},
                "severity": {"type": "string"},
            },
        ),
        _tool(
            "p2p_project_readiness_gap_show",
            "Show one stable project-readiness gap without mutation.",
            {"root": {"type": "string"}, "gap_id": {"type": "string"}},
            ["gap_id"],
        ),
        _tool(
            "p2p_project_questions_status",
            "List persistent project questions with bounded pagination; no lifecycle mutation.",
            {**page, "state": {"type": "string"}},
        ),
        _tool(
            "p2p_project_questions_next",
            "Show the next applicable project question without changing its state.",
            {"root": {"type": "string"}},
        ),
    ]
