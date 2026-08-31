from __future__ import annotations

from typing import Any

from p2p_engine.mcp.handlers.common import optional_string, required, to_jsonable
from p2p_engine.mcp.registry import PROMPT_TOOL_KINDS
from p2p_engine.services.project_application import ProjectApplicationService as P2PWorkspace


def handle_work_spec_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_intake_prompt":
        return {
            "intake": to_jsonable(
                workspace.create_intake_prompt(required(arguments, "idea"))
            )
        }
    if name == "p2p_project_brief_prompt":
        return {
            "project_brief_prompt": to_jsonable(
                workspace.create_project_brief_prompt()
            )
        }
    if name == "p2p_impact_prompt":
        path = workspace.generate_prompt(required(arguments, "proposal_id"), "impact")
        return {"impact_prompt": to_jsonable({"path": path})}
    if name == "p2p_change_status":
        return {"changes": to_jsonable(workspace.change_set_statuses())}
    if name == "p2p_change_show":
        return {
            "change": to_jsonable(
                workspace.show_change_set(required(arguments, "change_id"))
            )
        }
    if name == "p2p_change_tasks":
        return {
            "tasks": to_jsonable(
                workspace.change_set_tasks(required(arguments, "change_id"))
            )
        }
    if name == "p2p_work_list":
        return {"work": to_jsonable(workspace.work_statuses())}
    if name == "p2p_work_status":
        return {"work": to_jsonable(workspace.work_summaries())}
    if name == "p2p_work_show":
        return {
            "work": to_jsonable(workspace.show_work(required(arguments, "work_id")))
        }
    if name == "p2p_spec_lifecycle":
        return {
            "lifecycle": to_jsonable(
                workspace.software_spec_lifecycle(
                    optional_string(arguments, "intent") or "implementation_spec",
                    change_id=optional_string(arguments, "change_id"),
                    target=optional_string(arguments, "target"),
                )
            )
        }
    if name == "p2p_spec_status":
        return {"specs": to_jsonable(workspace.software_spec_statuses())}
    if name == "p2p_spec_show":
        change_id = required(arguments, "change_id")
        return {
            "change_id": change_id,
            "content": workspace.show_software_spec(change_id),
        }
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
        return {
            "spec": to_jsonable(
                workspace.refresh_software_spec(required(arguments, "change_id"))
            )
        }
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
    if name in PROMPT_TOOL_KINDS:
        path = workspace.generate_prompt(
            required(arguments, "proposal_id"),
            PROMPT_TOOL_KINDS[name],
        )
        return {PROMPT_TOOL_KINDS[name] + "_prompt": to_jsonable({"path": path})}
    if name == "p2p_spec_prompt":
        return {
            "spec_prompt": to_jsonable(
                workspace.create_software_spec_prompt(
                    required(arguments, "change_id")
                )
            )
        }
    return None
