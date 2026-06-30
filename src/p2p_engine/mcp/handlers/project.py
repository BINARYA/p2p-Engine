from __future__ import annotations

from pathlib import Path
from typing import Any

from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_project_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_agent_list":
        return {"agent_integrations": to_jsonable(workspace.agent_integrations_list())}
    if name == "p2p_agent_show":
        return {
            "agent_integration": to_jsonable(
                workspace.agent_integration_show(str(arguments.get("adapter") or "generic"))
            )
        }
    if name == "p2p_agent_doctor":
        return {"agent_doctor": to_jsonable(workspace.agent_doctor(str(arguments.get("adapter") or "all")))}
    if name == "p2p_validate":
        return {"validation": to_jsonable(workspace.validate())}
    if name == "p2p_context":
        return {
            "context": to_jsonable(
                workspace.context_packet(
                    budget=str(arguments.get("budget") or "small"),
                    target=optional_string(arguments, "target"),
                )
            )
        }
    if name == "p2p_assess_show":
        return {"assessment": to_jsonable(workspace.show_project_assessment())}
    if name == "p2p_project_rubrics_show":
        return {"rubrics": to_jsonable(workspace.show_project_rubrics())}
    if name == "p2p_maturity_show":
        return {"maturity": to_jsonable(workspace.show_definition_maturity())}
    if name == "p2p_intake_status":
        return {"intake_status": to_jsonable(workspace.intake_statuses())}
    if name == "p2p_project_brief_show":
        return {"operational_brief": workspace.show_project_brief()}
    if name == "p2p_choice_discover":
        return {"choice_discovery": to_jsonable(workspace.discover_choices())}
    if name == "p2p_conflict_status":
        return {"conflicts": to_jsonable(workspace.conflict_status())}
    if name == "p2p_project_status":
        return {"project_status": to_jsonable(workspace.project_state_status())}
    if name == "p2p_project_interaction_style_show":
        return {"interaction_style": to_jsonable(workspace.project_interaction_style())}
    if name == "p2p_project_interaction_style_set":
        return {
            "interaction_style": to_jsonable(
                workspace.set_project_interaction_style(
                    technical_verbosity=arguments.get("technical_verbosity"),
                    formality=arguments.get("formality"),
                    assertiveness=arguments.get("assertiveness"),
                    actor=str(arguments.get("actor") or "local"),
                )
            )
        }
    if name == "p2p_project_export":
        return {"export": to_jsonable(workspace.export_visible_project_definition())}
    if name == "p2p_project_export_status":
        return {"export_status": to_jsonable(workspace.visible_project_definition_export_status())}
    if name == "p2p_project_vertical_list":
        return {
            "verticals": to_jsonable(workspace.project_verticals()),
            "active": to_jsonable(workspace.active_project_vertical()),
        }
    if name == "p2p_project_vertical_show":
        return {"vertical": to_jsonable(workspace.show_project_vertical(required(arguments, "vertical_id")))}
    if name == "p2p_project_vertical_validate":
        return {"validation": to_jsonable(workspace.validate_project_vertical(required(arguments, "target")))}
    if name == "p2p_project_vertical_propose":
        return {"candidate": to_jsonable(workspace.propose_project_vertical(required(arguments, "idea")))}
    if name == "p2p_project_vertical_add":
        return {
            "vertical_add": to_jsonable(
                workspace.add_project_vertical(
                    Path(required(arguments, "source")),
                    activate=bool(arguments.get("activate") or False),
                    actor=str(arguments.get("actor") or "local"),
                )
            )
        }
    if name == "p2p_project_vertical_select":
        return {
            "active": to_jsonable(
                workspace.select_project_vertical(
                    required(arguments, "vertical_id"),
                    actor=str(arguments.get("actor") or "local"),
                )
            )
        }
    if name == "p2p_project_readiness_review":
        return {
            "readiness_review": to_jsonable(
                workspace.review_project_readiness(optional_string(arguments, "vertical_id"))
            )
        }
    if name == "p2p_next":
        top = arguments.get("top")
        limit = int(top) if top is not None else None
        return {"next_actions": to_jsonable(workspace.next_actions(limit=limit))}
    if name == "p2p_choice_list":
        return {"choices": to_jsonable(workspace.choice_statuses())}
    if name == "p2p_choice_show":
        return {"choice": to_jsonable(workspace.show_choice(required(arguments, "choice_id")))}
    if name == "p2p_registry_status":
        return {"registry_status": to_jsonable(workspace.registry_status())}
    if name == "p2p_registry_show":
        return {"registry": to_jsonable(workspace.show_registry(required(arguments, "name")))}
    if name == "p2p_project_show":
        section = required(arguments, "section")
        return {"section": section, "content": workspace.show_project_state(section)}
    return None
