from __future__ import annotations

from typing import Any

from p2p_engine.mcp.consent_audit import (
    consume_consent_with_audit,
    mark_consent_error_on_head_change,
    safe_head,
)
from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.mcp.registry import PROMPT_TOOL_KINDS
from p2p_engine.storage.filesystem import P2PWorkspace, WorkAcceptConflict


def handle_work_spec_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_intake_prompt":
        return {"intake": to_jsonable(workspace.create_intake_prompt(required(arguments, "idea")))}
    if name == "p2p_project_brief_prompt":
        return {"project_brief_prompt": to_jsonable(workspace.create_project_brief_prompt())}
    if name == "p2p_impact_prompt":
        path = workspace.generate_prompt(required(arguments, "proposal_id"), "impact")
        return {"impact_prompt": to_jsonable({"path": path})}
    if name == "p2p_change_status":
        return {"changes": to_jsonable(workspace.change_set_statuses())}
    if name == "p2p_change_show":
        return {"change": to_jsonable(workspace.show_change_set(required(arguments, "change_id")))}
    if name == "p2p_change_tasks":
        return {"tasks": to_jsonable(workspace.change_set_tasks(required(arguments, "change_id")))}
    if name == "p2p_work_list":
        return {"work": to_jsonable(workspace.work_statuses())}
    if name == "p2p_work_status":
        return {"work": to_jsonable(workspace.work_summaries())}
    if name == "p2p_work_show":
        return {"work": to_jsonable(workspace.show_work(required(arguments, "work_id")))}
    if name == "p2p_work_branch":
        return {
            "work_branch": to_jsonable(workspace.branch_work(required(arguments, "work_id"))),
            "governance": _preparatory_governance(),
        }
    if name == "p2p_work_submit":
        return {
            "work_submit": to_jsonable(workspace.submit_work(required(arguments, "work_id"))),
            "governance": _preparatory_governance(),
        }
    if name == "p2p_work_review":
        return {
            "work_review": to_jsonable(workspace.review_work(required(arguments, "work_id"))),
            "governance": _preparatory_governance(),
        }
    if name == "p2p_spec_status":
        return {"specs": to_jsonable(workspace.software_spec_statuses())}
    if name == "p2p_spec_show":
        change_id = required(arguments, "change_id")
        return {"change_id": change_id, "content": workspace.show_software_spec(change_id)}
    if name == "p2p_spec_export_status":
        return {"exports": to_jsonable(workspace.software_spec_export_statuses())}
    if name == "p2p_spec_export_show":
        change_id = required(arguments, "change_id")
        target = required(arguments, "target")
        return {
            "change_id": change_id,
            "target": target,
            "content": workspace.show_software_spec_export(change_id, target),
        }
    if name == "p2p_change_create":
        return {
            "change": to_jsonable(
                workspace.create_change_set(
                    source=required(arguments, "source"),
                    title=optional_string(arguments, "title"),
                )
            )
        }
    if name == "p2p_project_refresh":
        return {"written": to_jsonable(workspace.refresh_project_state())}
    if name == "p2p_spec_refresh":
        return {"spec": to_jsonable(workspace.refresh_software_spec(required(arguments, "change_id")))}
    if name == "p2p_spec_export":
        return {
            "export": to_jsonable(
                workspace.export_software_spec(
                    required(arguments, "change_id"),
                    required(arguments, "target"),
                )
            )
        }
    if name == "p2p_spec_export_validate":
        return {
            "validation": to_jsonable(
                workspace.validate_software_spec_export(
                    required(arguments, "change_id"),
                    required(arguments, "target"),
                )
            )
        }
    if name == "p2p_work_plan":
        return {
            "work": to_jsonable(
                workspace.create_work_plan(
                    required(arguments, "change_id"),
                    required(arguments, "target"),
                )
            )
        }
    if name == "p2p_work_publish":
        return _work_publish_tool(workspace, arguments)
    if name == "p2p_work_request_review":
        return _work_request_review_tool(workspace, arguments)
    if name == "p2p_work_accept":
        return _work_accept_tool(workspace, arguments)
    if name == "p2p_work_finalize":
        return _work_finalize_tool(workspace, arguments)
    if name == "p2p_work_cleanup":
        return _work_cleanup_tool(workspace, arguments)
    if name in PROMPT_TOOL_KINDS:
        path = workspace.generate_prompt(required(arguments, "proposal_id"), PROMPT_TOOL_KINDS[name])
        return {PROMPT_TOOL_KINDS[name] + "_prompt": to_jsonable({"path": path})}
    if name == "p2p_spec_prompt":
        return {"spec_prompt": to_jsonable(workspace.create_software_spec_prompt(required(arguments, "change_id")))}
    return None


def _preparatory_governance() -> dict[str, bool]:
    return {
        "owner_decision_required": False,
        "decision_made": False,
        "merge_performed": False,
        "published": False,
        "finalized": False,
        "cleanup_performed": False,
    }


def _validate_work_consent(
    workspace: P2PWorkspace,
    arguments: dict[str, Any],
    *,
    operation: str,
) -> tuple[str, str, str]:
    work_id = required(arguments, "work_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    workspace.consent_validate(
        consent_id,
        operation=operation,
        target=work_id,
        actor_id=actor_id,
    )
    return work_id, actor_id, consent_id


def _work_publish_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    operation = "work_publish"
    work_id, actor_id, consent_id = _validate_work_consent(workspace, arguments, operation=operation)
    before_head = safe_head(workspace)
    try:
        publish = workspace.publish_work(work_id, optional_string(arguments, "remote") or "origin")
    except ValueError as exc:
        mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), operation, work_id, actor_id)
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": operation,
            "target": publish.work_id,
            "actor_id": actor_id,
            "branch": publish.branch_name,
            "remote": publish.remote,
            "remote_url": publish.remote_url,
            "publish_commit": publish.publish_commit,
        },
        push_remote=publish.remote,
        push_branch_name=publish.branch_name,
    )
    return {
        "work_publish": to_jsonable(publish),
        "consent": to_jsonable(consumed),
        "governance": _privileged_governance(published=True),
    }


def _work_request_review_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    operation = "work_request_review"
    work_id, actor_id, consent_id = _validate_work_consent(workspace, arguments, operation=operation)
    before_head = safe_head(workspace)
    try:
        review = workspace.request_external_work_review(work_id, optional_string(arguments, "provider"))
    except ValueError as exc:
        mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), operation, work_id, actor_id)
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": operation,
            "target": review.work_id,
            "actor_id": actor_id,
            "branch": review.branch_name,
            "provider": review.provider,
            "remote": review.remote,
            "remote_url": review.remote_url,
            "metadata_commit": review.metadata_commit,
            "opens_external_request": False,
        },
        push_remote=review.remote,
        push_branch_name=review.branch_name,
    )
    return {
        "work_review_request": to_jsonable(review),
        "consent": to_jsonable(consumed),
        "governance": _privileged_governance(external_review_requested=True),
    }


def _work_accept_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    operation = "work_accept"
    work_id, actor_id, consent_id = _validate_work_consent(workspace, arguments, operation=operation)
    before_head = safe_head(workspace)
    try:
        accept = workspace.accept_work(work_id)
    except ValueError as exc:
        mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), operation, work_id, actor_id)
        raise
    if isinstance(accept, WorkAcceptConflict):
        conflict_receipt = workspace.consent_mark_used_with_error(
            consent_id,
            error="merge_conflict",
            result={
                "operation": operation,
                "target": work_id,
                "actor_id": actor_id,
                "branch": accept.branch_name,
                "base_branch": accept.base_branch,
                "conflicted_files": accept.conflicted_files,
                "head_before": before_head,
                "head_after": safe_head(workspace),
            },
        )
        return {
            "work_accept_conflict": to_jsonable(accept),
            "consent": to_jsonable(conflict_receipt),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
                "merge_performed": False,
                "manual_resolution_required": True,
                "finalized": False,
                "cleanup_performed": False,
            },
        }
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": operation,
            "target": accept.work_id,
            "actor_id": actor_id,
            "branch": accept.branch_name,
            "base_branch": accept.base_branch,
            "merge_commit": accept.merge_commit,
        },
    )
    return {
        "work_accept": to_jsonable(accept),
        "consent": to_jsonable(consumed),
        "governance": _privileged_governance(merge_performed=True),
    }


def _work_finalize_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    operation = "work_finalize"
    work_id, actor_id, consent_id = _validate_work_consent(workspace, arguments, operation=operation)
    before_head = safe_head(workspace)
    try:
        finalize = workspace.finalize_work(work_id, optional_string(arguments, "remote") or "origin")
    except ValueError as exc:
        mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), operation, work_id, actor_id)
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": operation,
            "target": finalize.work_id,
            "actor_id": actor_id,
            "base_branch": finalize.base_branch,
            "remote": finalize.remote,
            "remote_url": finalize.remote_url,
            "finalize_commit": finalize.finalize_commit,
        },
        push_remote=finalize.remote,
        push_branch_name=finalize.base_branch,
    )
    return {
        "work_finalize": to_jsonable(finalize),
        "consent": to_jsonable(consumed),
        "governance": _privileged_governance(merge_performed=True, finalized=True),
    }


def _work_cleanup_tool(workspace: P2PWorkspace, arguments: dict[str, Any]) -> dict[str, object]:
    operation = "work_cleanup"
    work_id, actor_id, consent_id = _validate_work_consent(workspace, arguments, operation=operation)
    before_head = safe_head(workspace)
    try:
        cleanup = workspace.cleanup_work(
            work_id,
            delete_remote=bool(arguments.get("delete_remote") or False),
            remote=optional_string(arguments, "remote") or "origin",
        )
    except ValueError as exc:
        mark_consent_error_on_head_change(workspace, consent_id, before_head, str(exc), operation, work_id, actor_id)
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": operation,
            "target": cleanup.work_id,
            "actor_id": actor_id,
            "branch": cleanup.branch_name,
            "base_branch": cleanup.base_branch,
            "remote": cleanup.remote,
            "local_deleted": cleanup.local_deleted,
            "remote_deleted": cleanup.remote_deleted,
            "cleanup_commit": cleanup.cleanup_commit,
        },
        push_remote=cleanup.remote,
        push_branch_name=cleanup.base_branch,
    )
    return {
        "work_cleanup": to_jsonable(cleanup),
        "consent": to_jsonable(consumed),
        "governance": _privileged_governance(cleanup_performed=True),
    }


def _privileged_governance(
    *,
    merge_performed: bool = False,
    published: bool = False,
    external_review_requested: bool = False,
    finalized: bool = False,
    cleanup_performed: bool = False,
) -> dict[str, bool]:
    return {
        "owner_decision_required": True,
        "decision_made": False,
        "merge_performed": merge_performed,
        "published": published,
        "external_review_requested": external_review_requested,
        "finalized": finalized,
        "cleanup_performed": cleanup_performed,
    }
