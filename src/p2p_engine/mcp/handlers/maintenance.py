from __future__ import annotations

from typing import Any

from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.services.project_application import ProjectApplicationService as P2PWorkspace


def handle_maintenance_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_init_project":
        starter = optional_string(arguments, "starter")
        vertical = optional_string(arguments, "vertical")
        if bool(starter) == bool(vertical):
            raise ValueError(
                "P2P_STRUCTURE_SOURCE_REQUIRED: MCP init requires exactly one of starter or vertical"
            )
        result = workspace.init_project_with_summary(
            name=required(arguments, "name"),
            agent_profile=str(arguments["agent"]) if arguments.get("agent") else None,
            project_domain=optional_string(arguments, "domain"),
            project_domain_name=str(arguments.get("domain_name") or ""),
            project_domain_source=str(arguments.get("domain_source") or "local"),
            project_domain_external_ref=optional_string(arguments, "domain_external_ref"),
            starter_id=starter,
            vertical_id=vertical,
            owner=optional_string(arguments, "owner"),
            storage_adapter=optional_string(arguments, "storage_adapter"),
        )
        return {
            "initialized": True,
            "root": to_jsonable(workspace.root),
            "created_or_updated": result.created,
            "agent_selection": to_jsonable(result.agent_selection),
            "mcp_hint": to_jsonable(result.mcp_hint),
            "project_domain": to_jsonable(result.domain),
            "structure_source": result.structure_source.to_dict(),
            "structure_origin": dict(result.structure_origin),
            "structure_revision": result.structure_revision,
            "project_identity": result.identity.to_dict(),
        }
    if name == "p2p_agent_instructions_refresh":
        result = workspace.refresh_agent_instructions(
            profile=str(arguments.get("profile") or "generic"),
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
                    starter=str(arguments.get("starter") or "generic"),
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
