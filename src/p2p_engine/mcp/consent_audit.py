from __future__ import annotations

from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.git import commit_all, head_commit, push_branch


def safe_head(workspace: P2PWorkspace) -> str | None:
    try:
        return head_commit(workspace.root)
    except Exception:
        return None


def sync_consent_target(workspace: P2PWorkspace, remote: str | None) -> str:
    status = workspace.sync_status(remote)
    if not status.branch:
        raise ValueError("Cannot resolve sync consent target from detached HEAD")
    selected_remote = remote or status.remote or "origin"
    return f"{selected_remote}/{status.branch}"


def consume_consent_with_audit(
    workspace: P2PWorkspace,
    consent_id: str,
    *,
    result: dict[str, object],
    push_remote: str | None = None,
    push_branch_name: str | None = None,
) -> object:
    consumed = workspace.consent_consume(consent_id, result=result)
    commit_and_push_consent_audit(
        workspace,
        consent_id,
        push_remote=push_remote,
        push_branch_name=push_branch_name,
    )
    return consumed


def commit_and_push_consent_audit(
    workspace: P2PWorkspace,
    consent_id: str,
    *,
    push_remote: str | None = None,
    push_branch_name: str | None = None,
) -> None:
    if commit_all(workspace.root, f"P2P consent consume {consent_id}") is None:
        raise ValueError(f"Failed to commit consent consumption audit for {consent_id}")
    if push_remote and push_branch_name and not push_branch(workspace.root, push_branch_name, push_remote):
        raise ValueError(f"Failed to push consent consumption audit for {consent_id}")


def mark_consent_error_on_head_change(
    workspace: P2PWorkspace,
    consent_id: str,
    before_head: str | None,
    error: str,
    operation: str,
    target: str,
    actor_id: str,
) -> None:
    after_head = safe_head(workspace)
    if before_head and after_head and before_head != after_head:
        workspace.consent_mark_used_with_error(
            consent_id,
            error=error,
            result={
                "operation": operation,
                "target": target,
                "actor_id": actor_id,
                "head_before": before_head,
                "head_after": after_head,
            },
        )
