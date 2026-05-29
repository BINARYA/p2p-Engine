from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from p2p_engine.core.contribution import ContributionType
from p2p_engine.storage.filesystem import P2PWorkspace


TOOL_NAMES = (
    "p2p_init_project",
    "p2p_agent_instructions_refresh",
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
    "p2p_intake_prompt",
    "p2p_intake_status",
    "p2p_project_brief_prompt",
    "p2p_project_brief_show",
    "p2p_choice_discover",
    "p2p_conflict_status",
    "p2p_impact_prompt",
    "p2p_project_status",
    "p2p_next",
    "p2p_proposal_list",
    "p2p_proposal_show",
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

_PROMPT_TOOL_KINDS = {
    "p2p_explore_prompt": "explore",
    "p2p_digest_prompt": "digest",
    "p2p_clarify_prompt": "clarify",
    "p2p_synthesize_prompt": "synthesize",
    "p2p_plan_prompt": "plan",
    "p2p_tasks_prompt": "tasks",
    "p2p_swot_prompt": "swot",
}


def _prompt_tool_definitions() -> list[dict[str, object]]:
    definitions = []
    for tool_name, kind in _PROMPT_TOOL_KINDS.items():
        definitions.append(
            {
                "name": tool_name,
                "description": (
                    f"Advisory prompt tool: generate a {kind} prompt for an existing "
                    "proposal. Does not import output or change decisions."
                ),
                "inputSchema": _schema(
                    {"root": {"type": "string"}, "proposal_id": {"type": "string"}},
                    ["proposal_id"],
                ),
            }
        )
    definitions.append(
        {
            "name": "p2p_spec_prompt",
            "description": (
                "Advisory prompt tool: generate a software-spec refinement prompt for "
                "a Change Set. Does not import output or change decisions."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "change_id": {"type": "string"}},
                ["change_id"],
            ),
        }
    )
    return definitions


def tool_definitions() -> list[dict[str, object]]:
    return [
        {
            "name": "p2p_init_project",
            "description": (
                "Write-safe bootstrap tool: initialize a P2P project and generate "
                "agent boundary instructions. Does not make governance decisions."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "name": {"type": "string"},
                    "agent": {
                        "type": "string",
                        "enum": ["generic", "codex", "claude", "all"],
                    },
                    "repository": {
                        "type": "string",
                        "enum": ["local", "cloud"],
                    },
                    "domain": {
                        "type": "string",
                        "enum": ["none", "custom", "generic", "software", "grant_document", "board_game"],
                    },
                },
                ["name"],
            ),
        },
        {
            "name": "p2p_agent_instructions_refresh",
            "description": (
                "Write-safe bootstrap tool: add or refresh agent instructions and "
                "agent policy. Does not remove other profiles or make decisions."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "profile": {
                        "type": "string",
                        "enum": ["generic", "codex", "claude", "all"],
                    },
                    "repository": {
                        "type": "string",
                        "enum": ["local", "cloud"],
                    },
                },
            ),
        },
        {
            "name": "p2p_registry_refresh",
            "description": (
                "Write-safe maintenance tool: regenerate deterministic P2P registries "
                "from existing project state. Does not decide or mutate proposals."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_validate",
            "description": (
                "Read-only validation tool: report structural and semantic P2P "
                "findings. Does not repair, refresh, or mutate project state."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_context",
            "description": (
                "Read-only token-aware context tool: return a compact deterministic "
                "context packet for agents before broad file reads."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "budget": {"type": "string", "enum": ["small", "medium"]},
                    "target": {"type": "string"},
                },
            ),
        },
        {
            "name": "p2p_assess_refresh",
            "description": (
                "Write-safe analysis tool: generate a deterministic project readiness "
                "assessment from current P2P state. Does not make governance decisions."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_assess_show",
            "description": (
                "Read-only analysis tool: show the stored project readiness assessment. "
                "Does not refresh or mutate project state."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_project_rubrics_init",
            "description": (
                "Write-safe project setup tool: create deterministic project definition "
                "rubrics for a domain. Does not make governance decisions."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "domain": {
                        "type": "string",
                        "enum": ["none", "custom", "generic", "software", "grant_document", "board_game"],
                    },
                    "force": {"type": "boolean"},
                },
            ),
        },
        {
            "name": "p2p_project_rubrics_show",
            "description": "Read configured project definition maturity rubrics.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_maturity_refresh",
            "description": (
                "Write-safe analysis tool: generate deterministic project definition "
                "maturity from configured rubrics. Does not assess implementation completeness."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_maturity_show",
            "description": "Read stored project definition maturity assessment.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_proposal_create",
            "description": (
                "Write-safe draft tool: create a draft P2P proposal using the core "
                "proposal scaffold. Does not accept, reject, defer, or decide."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "title": {"type": "string"},
                    "problem": {"type": "string"},
                    "context": {"type": "string"},
                    "goals": {"type": "array", "items": {"type": "string"}},
                    "non_goals": {"type": "array", "items": {"type": "string"}},
                    "proposal": {"type": "string"},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                },
                ["title"],
            ),
        },
        {
            "name": "p2p_proposal_update",
            "description": (
                "Write-safe refinement tool: update structured sections of an existing "
                "P2P proposal. Does not accept, reject, defer, or decide."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "problem": {"type": "string"},
                    "context": {"type": "string"},
                    "goals": {"type": "array", "items": {"type": "string"}},
                    "non_goals": {"type": "array", "items": {"type": "string"}},
                    "proposal": {"type": "string"},
                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                },
                ["proposal_id"],
            ),
        },
        {
            "name": "p2p_proposal_contribution_add",
            "description": (
                "Write-safe contribution tool: append a typed contribution to an "
                "existing proposal. Does not accept, reject, defer, merge, or decide."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "proposal_id": {"type": "string"},
                    "text": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": [item.value for item in ContributionType],
                    },
                    "relevance": {"type": "string"},
                    "author": {"type": "string"},
                },
                ["proposal_id", "text"],
            ),
        },
        {
            "name": "p2p_intake_prompt",
            "description": (
                "Write-safe draft tool: create an intake prompt for a raw idea. "
                "Does not apply recommendations or make governance decisions."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "idea": {"type": "string"}},
                ["idea"],
            ),
        },
        {
            "name": "p2p_intake_status",
            "description": "List intake records and whether analysis artifacts are populated.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_project_brief_prompt",
            "description": (
                "Advisory workflow tool: create project brief context and prompt artifacts "
                "from current project state. Does not import or decide."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_project_brief_show",
            "description": "Show the stored operational project brief if one has been imported.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_choice_discover",
            "description": (
                "Advisory analysis tool: discover choice candidates and blockers without "
                "creating, deciding, blocking, or unblocking choices."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_conflict_status",
            "description": "Read recorded project conflicts without recording new conflicts.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_impact_prompt",
            "description": (
                "Advisory analysis tool: generate an impact-analysis prompt for an "
                "existing proposal. Does not import impact output or change decisions."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "proposal_id": {"type": "string"}},
                ["proposal_id"],
            ),
        },
        {
            "name": "p2p_project_status",
            "description": "Show deterministic P2P project state status.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_next",
            "description": "Show advisory next actions from P2P project state.",
            "inputSchema": _schema({"root": {"type": "string"}, "top": {"type": "integer", "minimum": 1}}),
        },
        {
            "name": "p2p_proposal_list",
            "description": "List P2P proposals, optionally filtered by status.",
            "inputSchema": _schema({"root": {"type": "string"}, "status": {"type": "string"}}),
        },
        {
            "name": "p2p_proposal_show",
            "description": "Show one P2P proposal summary.",
            "inputSchema": _schema({"root": {"type": "string"}, "proposal_id": {"type": "string"}}, ["proposal_id"]),
        },
        {
            "name": "p2p_choice_list",
            "description": "List project choices.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_choice_show",
            "description": "Show one project choice.",
            "inputSchema": _schema({"root": {"type": "string"}, "choice_id": {"type": "string"}}, ["choice_id"]),
        },
        {
            "name": "p2p_change_status",
            "description": "List Change Set statuses.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_change_show",
            "description": "Show one Change Set summary.",
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_change_tasks",
            "description": "Show one Change Set task and action view.",
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_work_list",
            "description": "List P2P Work manifests.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_work_status",
            "description": "Show operational Work item summaries.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_work_show",
            "description": "Show one P2P Work manifest.",
            "inputSchema": _schema({"root": {"type": "string"}, "work_id": {"type": "string"}}, ["work_id"]),
        },
        {
            "name": "p2p_registry_status",
            "description": "Show generated registry availability and freshness checks.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_registry_show",
            "description": "Show a generated P2P registry.",
            "inputSchema": _schema({"root": {"type": "string"}, "name": {"type": "string"}}, ["name"]),
        },
        {
            "name": "p2p_project_show",
            "description": "Show a generated project definition section or feature document.",
            "inputSchema": _schema({"root": {"type": "string"}, "section": {"type": "string"}}, ["section"]),
        },
        {
            "name": "p2p_project_remote_show",
            "description": "Show local/cloud remote project profile metadata.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_status",
            "description": "List generated P2P-native software specs.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_show",
            "description": "Show a generated P2P-native software spec index.",
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_spec_export_status",
            "description": "List generated software spec exports.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_export_show",
            "description": "Show the primary document for an existing software spec export.",
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        {
            "name": "p2p_change_create",
            "description": (
                "Write-safe deterministic tool: create a metadata-only Change Set from "
                "an accepted proposal. Does not update status, branch, commit, or merge."
            ),
            "inputSchema": _schema(
                {"root": {"type": "string"}, "source": {"type": "string"}, "title": {"type": "string"}},
                ["source"],
            ),
        },
        {
            "name": "p2p_project_refresh",
            "description": (
                "Write-safe deterministic tool: refresh generated project definition files "
                "from accepted P2P state. Does not make governance decisions."
            ),
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_spec_refresh",
            "description": (
                "Write-safe deterministic tool: generate a P2P-native software spec from "
                "a Change Set. Does not import external edits."
            ),
            "inputSchema": _schema({"root": {"type": "string"}, "change_id": {"type": "string"}}, ["change_id"]),
        },
        {
            "name": "p2p_spec_export",
            "description": (
                "Write-safe deterministic tool: export generated spec artifacts for "
                "generic, OpenSpec, or Spec Kit targets."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        {
            "name": "p2p_spec_export_validate",
            "description": "Read-only validation tool: validate an existing software spec export.",
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        {
            "name": "p2p_work_plan",
            "description": (
                "Write-safe deterministic tool: create a Work manifest from a validated "
                "spec export. Does not create branches, commits, PRs, or merges."
            ),
            "inputSchema": _schema(
                {
                    "root": {"type": "string"},
                    "change_id": {"type": "string"},
                    "target": {"type": "string", "enum": ["generic", "openspec", "speckit"]},
                },
                ["change_id", "target"],
            ),
        },
        *_prompt_tool_definitions(),
    ]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, object]:
    arguments = arguments or {}
    root = Path(str(arguments.get("root") or Path.cwd()))
    workspace = P2PWorkspace(root)

    if name == "p2p_init_project":
        created = workspace.init_project(
            name=_required(arguments, "name"),
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
        return {"agent_instructions": _to_jsonable(result)}
    if name == "p2p_registry_refresh":
        return {"written": _to_jsonable(workspace.refresh_registries())}
    if name == "p2p_validate":
        return {"validation": _to_jsonable(workspace.validate())}
    if name == "p2p_context":
        return {
            "context": _to_jsonable(
                workspace.context_packet(
                    budget=str(arguments.get("budget") or "small"),
                    target=_optional_string(arguments, "target"),
                )
            )
        }
    if name == "p2p_assess_refresh":
        return {"assessment": _to_jsonable(workspace.refresh_project_assessment())}
    if name == "p2p_assess_show":
        return {"assessment": _to_jsonable(workspace.show_project_assessment())}
    if name == "p2p_project_rubrics_init":
        return {
            "rubrics": _to_jsonable(
                workspace.init_project_rubrics(
                    domain=str(arguments.get("domain") or "generic"),
                    force=bool(arguments.get("force") or False),
                )
            )
        }
    if name == "p2p_project_rubrics_show":
        return {"rubrics": _to_jsonable(workspace.show_project_rubrics())}
    if name == "p2p_maturity_refresh":
        return {"maturity": _to_jsonable(workspace.refresh_definition_maturity())}
    if name == "p2p_maturity_show":
        return {"maturity": _to_jsonable(workspace.show_definition_maturity())}
    if name == "p2p_proposal_create":
        proposal = workspace.create_proposal_with_details(
            title=_required(arguments, "title"),
            problem=_optional_string(arguments, "problem"),
            context=_optional_string(arguments, "context"),
            goals=_optional_string_list(arguments, "goals"),
            non_goals=_optional_string_list(arguments, "non_goals"),
            proposal=_optional_string(arguments, "proposal"),
            acceptance_criteria=_optional_string_list(arguments, "acceptance_criteria"),
        )
        return {
            "proposal": _to_jsonable(proposal),
            "governance": {
                "status": "draft",
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_update":
        path = workspace.update_proposal(
            proposal_id=_required(arguments, "proposal_id"),
            problem=_optional_string(arguments, "problem"),
            context=_optional_string(arguments, "context"),
            goals=_optional_string_list(arguments, "goals"),
            non_goals=_optional_string_list(arguments, "non_goals"),
            proposal=_optional_string(arguments, "proposal"),
            acceptance_criteria=_optional_string_list(arguments, "acceptance_criteria"),
        )
        return {
            "updated": _to_jsonable(path),
            "proposal": _to_jsonable(workspace.show_proposal(_required(arguments, "proposal_id"))),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_contribution_add":
        contribution = workspace.add_contribution(
            proposal_id=_required(arguments, "proposal_id"),
            contribution_type=_contribution_type(arguments),
            text=_required(arguments, "text"),
            relevance_hint=str(arguments.get("relevance") or "medium"),
            author=str(arguments.get("author") or "mcp"),
        )
        return {
            "contribution": _to_jsonable(contribution),
            "proposal": _to_jsonable(workspace.show_proposal(_required(arguments, "proposal_id"))),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_intake_prompt":
        return {"intake": _to_jsonable(workspace.create_intake_prompt(_required(arguments, "idea")))}
    if name == "p2p_intake_status":
        return {"intake_status": _to_jsonable(workspace.intake_statuses())}
    if name == "p2p_project_brief_prompt":
        return {"project_brief_prompt": _to_jsonable(workspace.create_project_brief_prompt())}
    if name == "p2p_project_brief_show":
        return {"operational_brief": workspace.show_project_brief()}
    if name == "p2p_choice_discover":
        return {"choice_discovery": _to_jsonable(workspace.discover_choices())}
    if name == "p2p_conflict_status":
        return {"conflicts": _to_jsonable(workspace.conflict_status())}
    if name == "p2p_impact_prompt":
        path = workspace.generate_prompt(_required(arguments, "proposal_id"), "impact")
        return {"impact_prompt": _to_jsonable({"path": path})}
    if name == "p2p_project_status":
        return {"project_status": _to_jsonable(workspace.project_state_status())}
    if name == "p2p_next":
        top = arguments.get("top")
        limit = int(top) if top is not None else None
        return {"next_actions": _to_jsonable(workspace.next_actions(limit=limit))}
    if name == "p2p_proposal_list":
        status = arguments.get("status")
        return {"proposals": _to_jsonable(workspace.proposal_summaries(str(status) if status else None))}
    if name == "p2p_proposal_show":
        return {"proposal": _to_jsonable(workspace.show_proposal(_required(arguments, "proposal_id")))}
    if name == "p2p_choice_list":
        return {"choices": _to_jsonable(workspace.choice_statuses())}
    if name == "p2p_choice_show":
        return {"choice": _to_jsonable(workspace.show_choice(_required(arguments, "choice_id")))}
    if name == "p2p_change_status":
        return {"changes": _to_jsonable(workspace.change_set_statuses())}
    if name == "p2p_change_show":
        return {"change": _to_jsonable(workspace.show_change_set(_required(arguments, "change_id")))}
    if name == "p2p_change_tasks":
        return {"tasks": _to_jsonable(workspace.change_set_tasks(_required(arguments, "change_id")))}
    if name == "p2p_work_list":
        return {"work": _to_jsonable(workspace.work_statuses())}
    if name == "p2p_work_status":
        return {"work": _to_jsonable(workspace.work_summaries())}
    if name == "p2p_work_show":
        return {"work": _to_jsonable(workspace.show_work(_required(arguments, "work_id")))}
    if name == "p2p_registry_status":
        return {"registry_status": _to_jsonable(workspace.registry_status())}
    if name == "p2p_registry_show":
        return {"registry": _to_jsonable(workspace.show_registry(_required(arguments, "name")))}
    if name == "p2p_project_show":
        section = _required(arguments, "section")
        return {"section": section, "content": workspace.show_project_state(section)}
    if name == "p2p_project_remote_show":
        return {"remote": _to_jsonable(workspace.remote_profile())}
    if name == "p2p_spec_status":
        return {"specs": _to_jsonable(workspace.software_spec_statuses())}
    if name == "p2p_spec_show":
        change_id = _required(arguments, "change_id")
        return {"change_id": change_id, "content": workspace.show_software_spec(change_id)}
    if name == "p2p_spec_export_status":
        return {"exports": _to_jsonable(workspace.software_spec_export_statuses())}
    if name == "p2p_spec_export_show":
        change_id = _required(arguments, "change_id")
        target = _required(arguments, "target")
        return {
            "change_id": change_id,
            "target": target,
            "content": workspace.show_software_spec_export(change_id, target),
        }
    if name == "p2p_change_create":
        return {
            "change": _to_jsonable(
                workspace.create_change_set(
                    source=_required(arguments, "source"),
                    title=_optional_string(arguments, "title"),
                )
            )
        }
    if name == "p2p_project_refresh":
        return {"written": _to_jsonable(workspace.refresh_project_state())}
    if name == "p2p_spec_refresh":
        return {"spec": _to_jsonable(workspace.refresh_software_spec(_required(arguments, "change_id")))}
    if name == "p2p_spec_export":
        return {
            "export": _to_jsonable(
                workspace.export_software_spec(
                    _required(arguments, "change_id"),
                    _required(arguments, "target"),
                )
            )
        }
    if name == "p2p_spec_export_validate":
        return {
            "validation": _to_jsonable(
                workspace.validate_software_spec_export(
                    _required(arguments, "change_id"),
                    _required(arguments, "target"),
                )
            )
        }
    if name == "p2p_work_plan":
        return {
            "work": _to_jsonable(
                workspace.create_work_plan(
                    _required(arguments, "change_id"),
                    _required(arguments, "target"),
                )
            )
        }
    if name in _PROMPT_TOOL_KINDS:
        path = workspace.generate_prompt(_required(arguments, "proposal_id"), _PROMPT_TOOL_KINDS[name])
        return {_PROMPT_TOOL_KINDS[name] + "_prompt": _to_jsonable({"path": path})}
    if name == "p2p_spec_prompt":
        return {"spec_prompt": _to_jsonable(workspace.create_software_spec_prompt(_required(arguments, "change_id")))}

    raise ValueError(f"Unknown MCP tool: {name}")


def _schema(properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def _required(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required argument: {name}")
    return str(value)


def _optional_string(arguments: dict[str, Any], name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_string_list(arguments: dict[str, Any], name: str) -> list[str] | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"Expected list argument: {name}")
    items = [str(item).strip() for item in value if str(item).strip()]
    return items or None


def _contribution_type(arguments: dict[str, Any]) -> ContributionType:
    value = str(arguments.get("type") or ContributionType.suggestion.value)
    try:
        return ContributionType(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ContributionType)
        raise ValueError(f"Invalid contribution type: {value}. Allowed: {allowed}") from exc


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value
