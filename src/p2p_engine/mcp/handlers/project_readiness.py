from __future__ import annotations

from typing import Any

from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_project_readiness_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_project_readiness_review":
        limit = int(arguments.get("limit") or 10)
        vertical_id = optional_string(arguments, "vertical_id")
        review = workspace.review_project_readiness(vertical_id)
        readiness = workspace.project_readiness_result(vertical_id)
        page = workspace.project_readiness_gaps(limit=limit)
        return {
            "project_readiness": to_jsonable(readiness),
            "readiness_review": to_jsonable(review),
            "gaps": to_jsonable(page),
            "mutation_performed": False,
        }
    if name == "p2p_project_readiness_gaps":
        page = workspace.project_readiness_gaps(
            kind=str(arguments.get("kind") or ""),
            severity=str(arguments.get("severity") or ""),
            limit=int(arguments.get("limit") or 20),
            cursor=str(arguments.get("cursor") or ""),
        )
        return {"project_readiness_page": to_jsonable(page), "mutation_performed": False}
    if name == "p2p_project_readiness_gap_show":
        gap = workspace.project_readiness_gap(required(arguments, "gap_id"))
        return {"project_readiness_gap": to_jsonable(gap), "mutation_performed": False}
    if name == "p2p_project_questions_status":
        page = workspace.project_questions_page(
            state=str(arguments.get("state") or ""),
            limit=int(arguments.get("limit") or 20),
            cursor=str(arguments.get("cursor") or ""),
        )
        return {"project_questions": to_jsonable(page), "mutation_performed": False}
    if name == "p2p_project_questions_next":
        question = workspace.next_project_question()
        return {"project_question": to_jsonable(question), "mutation_performed": False}
    return None
