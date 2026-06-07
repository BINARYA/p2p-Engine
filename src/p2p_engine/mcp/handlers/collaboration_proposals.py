from __future__ import annotations

from typing import Any

from p2p_engine.mcp.consent_audit import (
    commit_and_push_consent_audit,
    consume_consent_with_audit,
    mark_consent_error_on_head_change,
    safe_head,
)
from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.storage.filesystem import P2PWorkspace, ProposalMergeConflict


def handle_collaboration_proposal_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_proposal_draft_commit":
        return {
            "proposal_draft_commit": to_jsonable(
                workspace.commit_proposal_draft(
                    required(arguments, "proposal_id"),
                    actor=str(arguments.get("actor") or "local"),
                )
            ),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "published": False,
            },
        }
    if name == "p2p_proposal_branch":
        return {
            "proposal_branch": to_jsonable(
                workspace.branch_proposal(
                    required(arguments, "proposal_id"),
                    actor=str(arguments.get("actor") or "local"),
                    base_branch=str(arguments.get("base_branch") or "main"),
                    allow_proposal_base=bool(arguments.get("allow_proposal_base") or False),
                )
            ),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "merge_performed": False,
            },
        }
    if name == "p2p_proposal_branch_status":
        return {"proposal_branch": to_jsonable(workspace.show_proposal_branch(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_publish":
        return _proposal_publish_tool(workspace, arguments)
    if name == "p2p_proposal_request_review":
        return _proposal_request_review_tool(workspace, arguments)
    if name == "p2p_proposal_accept_branch":
        return _proposal_accept_branch_tool(workspace, arguments)
    if name == "p2p_proposal_reject_branch":
        return _proposal_reject_branch_tool(workspace, arguments)
    if name == "p2p_proposal_merge":
        return _proposal_merge_tool(workspace, arguments)
    if name == "p2p_proposal_finalize":
        return _proposal_finalize_tool(workspace, arguments)
    if name == "p2p_proposal_cleanup":
        return _proposal_cleanup_tool(workspace, arguments)
    return None


def _proposal_publish_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation="proposal_publish",
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        branch = workspace.publish_proposal_branch(
            proposal_id,
            optional_string(arguments, "remote"),
            auto_renumber=bool(arguments.get("auto_renumber") or False),
        )
    except ValueError as exc:
        after_head = safe_head(workspace)
        if before_head and after_head and before_head != after_head:
            workspace.consent_mark_used_with_error(
                consent_id,
                error=str(exc),
                result={
                    "operation": "proposal_publish",
                    "target": proposal_id,
                    "actor_id": actor_id,
                    "head_before": before_head,
                    "head_after": after_head,
                },
            )
        raise
    consumed = workspace.consent_consume(
        consent_id,
        result={
            "operation": "proposal_publish",
            "target": branch.proposal_id,
            "actor_id": actor_id,
            "branch": branch.branch_name,
            "remote": branch.remote,
            "remote_branch": branch.metadata.get("remote_branch"),
        },
    )
    commit_and_push_consent_audit(workspace, consent_id, push_remote=branch.remote, push_branch_name=branch.branch_name)
    return {
        "proposal_branch": to_jsonable(branch),
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": False,
            "merge_performed": False,
        },
    }


def _proposal_request_review_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation="proposal_request_review",
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        branch = workspace.request_proposal_branch_review(
            proposal_id,
            optional_string(arguments, "provider"),
        )
    except ValueError as exc:
        mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            "proposal_request_review",
            proposal_id,
            actor_id,
        )
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "proposal_request_review",
            "target": branch.proposal_id,
            "actor_id": actor_id,
            "branch": branch.branch_name,
            "remote": branch.remote,
            "review": branch.metadata.get("review"),
        },
        push_remote=branch.remote,
        push_branch_name=branch.branch_name,
    )
    return {
        "proposal_branch": to_jsonable(branch),
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": False,
            "merge_performed": False,
        },
    }


def _proposal_accept_branch_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation="proposal_accept_branch",
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        branch = workspace.accept_proposal_branch(proposal_id, required(arguments, "reason"))
    except ValueError as exc:
        mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            "proposal_accept_branch",
            proposal_id,
            actor_id,
        )
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "proposal_accept_branch",
            "target": branch.proposal_id,
            "actor_id": actor_id,
            "branch": branch.branch_name,
            "status": branch.status,
            "decision": branch.metadata.get("branch_decision"),
        },
        push_remote=branch.remote,
        push_branch_name=branch.branch_name,
    )
    return {
        "proposal_branch": to_jsonable(branch),
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": True,
            "decision_outcome": "accepted",
            "merge_performed": False,
        },
    }


def _proposal_reject_branch_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation="proposal_reject_branch",
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        branch = workspace.reject_proposal_branch(proposal_id, required(arguments, "reason"))
    except ValueError as exc:
        mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            "proposal_reject_branch",
            proposal_id,
            actor_id,
        )
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "proposal_reject_branch",
            "target": branch.proposal_id,
            "actor_id": actor_id,
            "branch": branch.branch_name,
            "status": branch.status,
            "decision": branch.metadata.get("branch_decision"),
        },
        push_remote=branch.remote,
        push_branch_name=branch.branch_name,
    )
    return {
        "proposal_branch": to_jsonable(branch),
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": True,
            "decision_outcome": "rejected",
            "merge_performed": False,
        },
    }


def _proposal_merge_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation="proposal_merge",
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        merge = workspace.merge_proposal_branch(proposal_id)
    except ValueError as exc:
        mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            "proposal_merge",
            proposal_id,
            actor_id,
        )
        raise
    if isinstance(merge, ProposalMergeConflict):
        conflict_receipt = workspace.consent_mark_used_with_error(
            consent_id,
            error="merge_conflict",
            result={
                "operation": "proposal_merge",
                "target": proposal_id,
                "actor_id": actor_id,
                "branch": merge.branch_name,
                "base_branch": merge.base_branch,
                "conflicted_files": merge.conflicted_files,
                "head_before": before_head,
                "head_after": safe_head(workspace),
            },
        )
        return {
            "proposal_merge_conflict": to_jsonable(merge),
            "consent": to_jsonable(conflict_receipt),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
                "merge_performed": False,
                "manual_resolution_required": True,
            },
        }
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "proposal_merge",
            "target": merge.proposal_id,
            "actor_id": actor_id,
            "branch": merge.branch_name,
            "base_branch": merge.base_branch,
            "merge_commit": merge.merge_commit,
        },
    )
    return {
        "proposal_merge": to_jsonable(merge),
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": False,
            "merge_performed": True,
        },
    }


def _proposal_finalize_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation="proposal_finalize",
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        finalize = workspace.finalize_proposal_branch(
            proposal_id,
            optional_string(arguments, "remote"),
        )
    except ValueError as exc:
        mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            "proposal_finalize",
            proposal_id,
            actor_id,
        )
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "proposal_finalize",
            "target": finalize.proposal_id,
            "actor_id": actor_id,
            "branch": finalize.branch_name,
            "base_branch": finalize.base_branch,
            "remote": finalize.remote,
            "finalize_commit": finalize.finalize_commit,
        },
        push_remote=finalize.remote,
        push_branch_name=finalize.base_branch,
    )
    return {
        "proposal_finalize": to_jsonable(finalize),
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": False,
            "merge_performed": True,
            "finalized": True,
            "cleanup_performed": False,
        },
    }


def _proposal_cleanup_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation="proposal_cleanup",
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        cleanup = workspace.cleanup_proposal_branch(
            proposal_id,
            delete_remote=bool(arguments.get("delete_remote") or False),
            remote=optional_string(arguments, "remote"),
        )
    except ValueError as exc:
        mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            "proposal_cleanup",
            proposal_id,
            actor_id,
        )
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": "proposal_cleanup",
            "target": cleanup.proposal_id,
            "actor_id": actor_id,
            "branch": cleanup.branch_name,
            "base_branch": cleanup.base_branch,
            "remote": cleanup.remote,
            "local_deleted": cleanup.local_deleted,
            "remote_deleted": cleanup.remote_deleted,
            "cleanup_commit": cleanup.cleanup_commit,
        },
        push_remote=cleanup.remote if cleanup.remote_url else None,
        push_branch_name=cleanup.base_branch if cleanup.remote_url else None,
    )
    return {
        "proposal_cleanup": to_jsonable(cleanup),
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": False,
            "merge_performed": False,
            "cleanup_performed": True,
        },
    }
