from __future__ import annotations

from p2p_engine.mcp.registry import PROMPT_TOOL_KINDS, TOOL_NAMES, tool_definitions
from p2p_engine.mcp.tools import TOOL_NAMES as COMPAT_TOOL_NAMES
from p2p_engine.mcp.tools import tool_definitions as compat_tool_definitions


EXPECTED_TOOL_NAMES = (
    "p2p_init_project",
    "p2p_agent_instructions_refresh",
    "p2p_agent_list",
    "p2p_agent_show",
    "p2p_agent_doctor",
    "p2p_agent_install",
    "p2p_agent_update",
    "p2p_agent_uninstall",
    "p2p_registry_refresh",
    "p2p_validate",
    "p2p_context",
    "p2p_assess_refresh",
    "p2p_assess_show",
    "p2p_project_rubrics_init",
    "p2p_project_rubrics_show",
    "p2p_maturity_refresh",
    "p2p_maturity_show",
    "p2p_proposal_create",
    "p2p_proposal_update",
    "p2p_proposal_contribution_add",
    "p2p_proposal_contribution_list",
    "p2p_intake_prompt",
    "p2p_intake_status",
    "p2p_project_brief_prompt",
    "p2p_project_brief_show",
    "p2p_choice_discover",
    "p2p_conflict_status",
    "p2p_governance_status",
    "p2p_governance_validate",
    "p2p_choice_governance_preflight",
    "p2p_vote_status",
    "p2p_precedent_search",
    "p2p_impact_prompt",
    "p2p_project_status",
    "p2p_project_interaction_style_show",
    "p2p_project_interaction_style_set",
    "p2p_project_export",
    "p2p_project_export_status",
    "p2p_project_vertical_list",
    "p2p_project_vertical_show",
    "p2p_project_vertical_validate",
    "p2p_project_vertical_propose",
    "p2p_project_vertical_add",
    "p2p_project_vertical_select",
    "p2p_project_vertical_lock_show",
    "p2p_project_vertical_lock_repair",
    "p2p_project_context",
    "p2p_project_sections",
    "p2p_project_section_show",
    "p2p_project_definition_show",
    "p2p_project_definition_update",
    "p2p_project_readiness_review",
    "p2p_next",
    "p2p_next_add",
    "p2p_next_complete",
    "p2p_next_retire",
    "p2p_next_refresh",
    "p2p_proposal_list",
    "p2p_proposal_show",
    "p2p_proposal_readiness_get",
    "p2p_proposal_readiness_init",
    "p2p_proposal_readiness_refresh",
    "p2p_proposal_readiness_assess",
    "p2p_proposal_readiness_explain",
    "p2p_proposal_readiness_list_gaps",
    "p2p_proposal_readiness_review",
    "p2p_proposal_questions_status",
    "p2p_proposal_questions_init",
    "p2p_proposal_questions_add",
    "p2p_proposal_questions_answer",
    "p2p_proposal_questions_next",
    "p2p_proposal_questions_apply",
    "p2p_proposal_artifact_status",
    "p2p_proposal_artifact_init",
    "p2p_proposal_artifact_set",
    "p2p_proposal_artifact_confirm",
    "p2p_proposal_artifact_mark_legacy",
    "p2p_choice_list",
    "p2p_choice_show",
    "p2p_change_status",
    "p2p_change_show",
    "p2p_change_tasks",
    "p2p_work_list",
    "p2p_work_status",
    "p2p_work_show",
    "p2p_registry_status",
    "p2p_registry_show",
    "p2p_project_show",
    "p2p_project_remote_show",
    "p2p_project_remote_configure",
    "p2p_permissions_show",
    "p2p_consent_request",
    "p2p_consent_status",
    "p2p_consent_show",
    "p2p_sync_status",
    "p2p_sync_fetch",
    "p2p_sync_pull",
    "p2p_sync_push",
    "p2p_proposal_branch",
    "p2p_proposal_draft_commit",
    "p2p_proposal_branch_status",
    "p2p_proposal_publish",
    "p2p_proposal_request_review",
    "p2p_proposal_accept",
    "p2p_proposal_reject",
    "p2p_proposal_defer",
    "p2p_proposal_accept_branch",
    "p2p_proposal_reject_branch",
    "p2p_proposal_merge",
    "p2p_proposal_finalize",
    "p2p_proposal_cleanup",
    "p2p_proposal_branch_scan",
    "p2p_spec_status",
    "p2p_spec_show",
    "p2p_spec_export_status",
    "p2p_spec_export_show",
    "p2p_change_create",
    "p2p_project_refresh",
    "p2p_spec_refresh",
    "p2p_spec_export",
    "p2p_spec_export_validate",
    "p2p_work_plan",
    "p2p_explore_prompt",
    "p2p_digest_prompt",
    "p2p_clarify_prompt",
    "p2p_synthesize_prompt",
    "p2p_plan_prompt",
    "p2p_tasks_prompt",
    "p2p_swot_prompt",
    "p2p_spec_prompt",
)


def test_mcp_registry_definitions_match_declared_tool_names() -> None:
    definitions = tool_definitions()
    names = [definition["name"] for definition in definitions]

    assert len(names) == len(set(names))
    assert set(names) == set(TOOL_NAMES)
    assert names == list(TOOL_NAMES)
    assert TOOL_NAMES == EXPECTED_TOOL_NAMES


def test_mcp_registry_definitions_use_strict_object_schemas() -> None:
    for definition in tool_definitions():
        schema = definition["inputSchema"]

        assert definition["name"] in TOOL_NAMES
        assert definition["description"]
        assert schema["type"] == "object"
        assert isinstance(schema["properties"], dict)
        assert isinstance(schema["required"], list)
        assert schema["additionalProperties"] is False


def test_mcp_tools_module_reexports_registry_surface() -> None:
    assert COMPAT_TOOL_NAMES is TOOL_NAMES
    assert compat_tool_definitions is tool_definitions


def test_mcp_prompt_tool_mapping_is_available_for_dispatch() -> None:
    prompt_names = set(PROMPT_TOOL_KINDS)
    definition_names = {definition["name"] for definition in tool_definitions()}

    assert prompt_names <= definition_names
    assert PROMPT_TOOL_KINDS["p2p_explore_prompt"] == "explore"
    assert PROMPT_TOOL_KINDS["p2p_swot_prompt"] == "swot"
