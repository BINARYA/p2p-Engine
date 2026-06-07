from __future__ import annotations

from typing import Any

from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_maintenance_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_init_project":
        created = workspace.init_project(
            name=required(arguments, "name"),
            agent_profile=str(arguments.get("agent") or "generic"),
            repository_mode=str(arguments.get("repository") or "local"),
            project_domain=str(arguments.get("domain") or "none"),
        )
        return {
            "initialized": True,
            "root": workspace.root,
            "created_or_updated": created,
        }
    if name == "p2p_agent_instructions_refresh":
        repository = arguments.get("repository")
        result = workspace.refresh_agent_instructions(
            profile=str(arguments.get("profile") or "generic"),
            repository_mode=str(repository) if repository is not None else None,
        )
        return {"agent_instructions": to_jsonable(result)}
    if name == "p2p_agent_install":
        return {
            "agent_integration": to_jsonable(
                workspace.install_agent_integrations(
                    str(arguments.get("adapter") or "all"),
                    force=bool(arguments.get("force") or False),
                )
            )
        }
    if name == "p2p_agent_update":
        return {
            "agent_integration": to_jsonable(
                workspace.install_agent_integrations(
                    str(arguments.get("adapter") or "all"),
                    force=bool(arguments.get("force") or False),
                )
            )
        }
    if name == "p2p_agent_uninstall":
        return {
            "agent_integration": to_jsonable(
                workspace.uninstall_agent_integration(str(arguments.get("adapter") or ""))
            )
        }
    if name == "p2p_registry_refresh":
        return {"written": to_jsonable(workspace.refresh_registries())}
    if name == "p2p_assess_refresh":
        return {"assessment": to_jsonable(workspace.refresh_project_assessment())}
    if name == "p2p_project_rubrics_init":
        return {
            "rubrics": to_jsonable(
                workspace.init_project_rubrics(
                    domain=str(arguments.get("domain") or "generic"),
                    force=bool(arguments.get("force") or False),
                )
            )
        }
    if name == "p2p_maturity_refresh":
        return {"maturity": to_jsonable(workspace.refresh_definition_maturity())}
    if name == "p2p_next_add":
        action = workspace.next_action_add(
            kind=required(arguments, "kind"),
            target=str(arguments.get("target") or ""),
            reason=required(arguments, "reason"),
            command=str(arguments.get("command") or ""),
            priority=str(arguments.get("priority") or "medium"),
            action_id=optional_string(arguments, "action_id"),
        )
        return {"next_action": to_jsonable(action)}
    if name == "p2p_next_complete":
        return {
            "next_action_result": to_jsonable(
                workspace.next_action_complete(
                    required(arguments, "action_id"),
                    required(arguments, "reason"),
                )
            )
        }
    if name == "p2p_next_retire":
        return {
            "next_action_result": to_jsonable(
                workspace.next_action_retire(
                    required(arguments, "action_id"),
                    required(arguments, "reason"),
                )
            )
        }
    if name == "p2p_next_refresh":
        return {"next_action_refresh": to_jsonable(workspace.next_actions_refresh())}
    return None
