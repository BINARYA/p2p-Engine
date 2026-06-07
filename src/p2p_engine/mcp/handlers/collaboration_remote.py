from __future__ import annotations

from typing import Any

from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_collaboration_remote_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_project_remote_show":
        return {"remote": to_jsonable(workspace.remote_profile())}
    if name == "p2p_project_remote_configure":
        profile = workspace.configure_remote_profile(
            mode=required(arguments, "mode"),
            provider=optional_string(arguments, "provider"),
            remote=str(arguments.get("remote") or "origin"),
            url=optional_string(arguments, "url"),
        )
        return {
            "remote": to_jsonable(profile),
            "sync": to_jsonable(workspace.sync_status(profile.remote)),
            "provider_side_effects": {
                "creates_remote_repository": False,
                "opens_external_request": False,
                "changes_git_remote": False,
            },
        }
    if name == "p2p_permissions_show":
        return {"permissions": to_jsonable(workspace.permissions_show())}
    if name == "p2p_consent_request":
        consent = workspace.consent_request(
            operation=required(arguments, "operation"),
            target=required(arguments, "target"),
            actor_id=required(arguments, "actor_id"),
            requested_by=optional_string(arguments, "requested_by"),
            scope=optional_string(arguments, "scope"),
            expires_on=optional_string(arguments, "expires_on"),
        )
        return {
            "consent": to_jsonable(consent),
            "governance": {
                "owner_decision_required": True,
                "consent_granted": False,
                "execution_authorized": False,
                "next": "Owner must grant consent through CLI, UI, or an authenticated server workflow.",
            },
        }
    if name == "p2p_consent_status":
        return {"consents": to_jsonable(workspace.consent_statuses())}
    if name == "p2p_consent_show":
        return {"consent": to_jsonable(workspace.consent_show(required(arguments, "consent_id")))}
    return None
