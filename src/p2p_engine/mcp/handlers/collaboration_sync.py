from __future__ import annotations

from typing import Any

from p2p_engine.mcp.consent_audit import (
    consume_consent_with_audit,
    mark_consent_error_on_head_change,
    safe_head,
    sync_consent_target,
)
from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_collaboration_sync_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_sync_status":
        return {"sync": to_jsonable(workspace.sync_status(optional_string(arguments, "remote")))}
    if name == "p2p_sync_fetch":
        return {"sync": to_jsonable(workspace.sync_fetch(optional_string(arguments, "remote")))}
    if name == "p2p_sync_pull":
        return _sync_pull_tool(workspace, arguments)
    if name == "p2p_sync_push":
        return _sync_push_tool(workspace, arguments)
    return None


def _sync_pull_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    before_head = safe_head(workspace)
    target = sync_consent_target(workspace, optional_string(arguments, "remote"))
    workspace.consent_validate(consent_id, operation="sync_pull", target=target, actor_id=actor_id)
    try:
        result = workspace.sync_pull(optional_string(arguments, "remote"))
    except ValueError as exc:
        mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), "sync_pull", target, actor_id)
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "sync_pull",
            "target": target,
            "actor_id": actor_id,
            "branch": result.branch,
            "remote": result.remote,
            "head_before": before_head,
            "head_after": safe_head(workspace),
        },
        push_remote=result.remote,
        push_branch_name=result.branch,
    )
    return {"sync": to_jsonable(result), "consent": to_jsonable(consumed)}


def _sync_push_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    target = sync_consent_target(workspace, optional_string(arguments, "remote"))
    workspace.consent_validate(consent_id, operation="sync_push", target=target, actor_id=actor_id)
    before_head = safe_head(workspace)
    try:
        result = workspace.sync_push(optional_string(arguments, "remote"))
    except ValueError as exc:
        mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), "sync_push", target, actor_id)
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "sync_push",
            "target": target,
            "actor_id": actor_id,
            "branch": result.branch,
            "remote": result.remote,
            "head_before": before_head,
            "head_after": safe_head(workspace),
        },
        push_remote=result.remote,
        push_branch_name=result.branch,
    )
    return {"sync": to_jsonable(result), "consent": to_jsonable(consumed)}
