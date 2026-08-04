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
    if name == "p2p_governance_status":
        return {
            "governance_status": to_jsonable(workspace.governance_status()),
            "mutation_performed": False,
        }
    if name == "p2p_governance_validate":
        return {
            "governance_validation": to_jsonable(workspace.validate_governance_policy()),
            "mutation_performed": False,
        }
    if name == "p2p_choice_governance_preflight":
        return {
            "governance_preflight": to_jsonable(
                workspace.choice_governance_preflight(
                    required(arguments, "choice_id"),
                    option=required(arguments, "option"),
                    actor=required(arguments, "actor"),
                    precedent_id=optional_string(arguments, "precedent_id"),
                    tag=optional_string(arguments, "tag"),
                )
            ),
            "decision_made": False,
            "mutation_performed": False,
        }
    if name == "p2p_vote_status":
        return {
            "vote_status": to_jsonable(workspace.vote_status(required(arguments, "proposal_id"))),
            "mutation_performed": False,
        }
    if name == "p2p_precedent_search":
        return {
            "precedents": to_jsonable(
                workspace.search_decision_precedents(
                    precedent_id=optional_string(arguments, "precedent_id"),
                    proposal_id=optional_string(arguments, "proposal_id"),
                    choice_id=optional_string(arguments, "choice_id"),
                    tag=optional_string(arguments, "tag"),
                )
            ),
            "mutation_performed": False,
        }
    if name == "p2p_workspace_schema_status":
        return {
            "workspace_schema": workspace.workspace_schema_status().to_dict(),
            "mutation_performed": False,
        }
    if name == "p2p_proposal_vertical_coverage_show":
        return {
            "vertical_coverage": to_jsonable(
                workspace.proposal_vertical_coverage_status(required(arguments, "proposal_id"))
            ),
            "mutation_performed": False,
        }
    if name == "p2p_proposal_vertical_coverage_suggest":
        return {
            "vertical_coverage_suggestion": to_jsonable(
                workspace.suggest_proposal_vertical_coverage(required(arguments, "proposal_id"))
            ),
            "mutation_performed": False,
        }
    if name == "p2p_project_status":
        return {"project_status": to_jsonable(workspace.project_state_status())}
    if name == "p2p_project_progress":
        return {"project_progress": to_jsonable(workspace.project_progress()), "mutation_performed": False}
    if name == "p2p_project_freshness":
        return {"project_freshness": to_jsonable(workspace.project_freshness()), "mutation_performed": False}
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
    if name == "p2p_project_publish_prepare":
        return {
            "publication_prepare": to_jsonable(
                workspace.prepare_project_publication(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                    contributions=str(arguments.get("contributions") or "auto"),
                )
            )
        }
    if name == "p2p_project_publish_import":
        return {
            "publication_import": to_jsonable(
                workspace.import_project_publication(
                    Path(required(arguments, "source")),
                    model=(Path(str(arguments["model"])) if arguments.get("model") else None),
                    evidence_accounting=(
                        Path(str(arguments["evidence_accounting"]))
                        if arguments.get("evidence_accounting")
                        else None
                    ),
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_validate":
        return {
            "publication_validation": to_jsonable(
                workspace.validate_project_publication(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_render":
        return {
            "publication_render": to_jsonable(
                workspace.render_project_publication(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_status":
        return {
            "publication_status": to_jsonable(
                workspace.project_publication_status(
                    language=str(arguments.get("language") or "en"),
                    output_name=str(arguments.get("output_name") or "project"),
                )
            )
        }
    if name == "p2p_project_publish_list":
        return {"publication_editions": to_jsonable(workspace.project_publication_editions())}
    if name == "p2p_project_vertical_list":
        return {
            "verticals": to_jsonable(workspace.project_verticals()),
            "active": to_jsonable(workspace.active_project_vertical()),
        }
    if name == "p2p_project_vertical_show":
        return {"vertical": to_jsonable(workspace.show_project_vertical(required(arguments, "vertical_id")))}
    if name == "p2p_project_vertical_validate":
        return {"validation": to_jsonable(workspace.validate_project_vertical(required(arguments, "target")))}
    if name == "p2p_project_vertical_select":
        modules = arguments.get("modules")
        if modules is not None and not isinstance(modules, list):
            raise ValueError("Expected list argument: modules")
        return {
            "active": to_jsonable(
                workspace.select_project_vertical(
                    required(arguments, "vertical_id"),
                    actor=str(arguments.get("actor") or "local"),
                    profile=str(arguments.get("profile") or "default"),
                    modules=[str(item) for item in modules if str(item).strip()] if isinstance(modules, list) else None,
                )
            ),
            "lock_status": to_jsonable(workspace.project_vertical_lock_status()),
            "definition": to_jsonable(workspace.project_definition_view()),
        }
    if name == "p2p_project_vertical_lock_show":
        return {"lock_status": to_jsonable(workspace.project_vertical_lock_status())}
    if name == "p2p_project_vertical_lock_repair":
        return {
            "lock": to_jsonable(
                workspace.repair_project_vertical_lock(actor=str(arguments.get("actor") or "local"))
            )
        }
    if name == "p2p_project_context":
        return {"project_context": to_jsonable(workspace.project_vertical_context())}
    if name == "p2p_project_sections":
        return {
            "sections": to_jsonable(
                workspace.project_vertical_sections(optional_string(arguments, "vertical_id"))
            )
        }
    if name == "p2p_project_section_show":
        return {
            "section": to_jsonable(
                workspace.project_vertical_section(
                    required(arguments, "section_id"),
                    optional_string(arguments, "vertical_id"),
                )
            )
        }
    if name == "p2p_project_definition_show":
        return {"definition": to_jsonable(workspace.project_definition_view())}
    if name == "p2p_project_definition_update":
        return {
            "definition_update": to_jsonable(
                workspace.update_project_definition(Path(required(arguments, "patch")))
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
    if name == "p2p_project_memory_status":
        return {
            "project_memory_status": to_jsonable(workspace.vertical_project_memory_status()),
            "mutation_performed": False,
        }
    if name == "p2p_project_memory_show":
        return {
            "project_memory": to_jsonable(
                workspace.show_vertical_project_memory(
                    section_id=optional_string(arguments, "section"),
                    include_history=bool(arguments.get("include_history") or False),
                    limit=int(arguments.get("limit", 20)),
                    cursor=str(arguments.get("cursor") or ""),
                )
            ),
            "mutation_performed": False,
        }
    if name == "p2p_project_show":
        section = required(arguments, "section")
        return {"section": section, "content": workspace.show_project_state(section)}
    return None
