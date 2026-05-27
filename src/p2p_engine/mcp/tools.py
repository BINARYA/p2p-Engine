from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from p2p_engine.storage.filesystem import P2PWorkspace


TOOL_NAMES = (
    "p2p_init_project",
    "p2p_agent_instructions_refresh",
    "p2p_registry_refresh",
    "p2p_proposal_create",
    "p2p_proposal_update",
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
    "p2p_work_status",
    "p2p_registry_show",
)


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
            "name": "p2p_work_status",
            "description": "Show operational Work item summaries.",
            "inputSchema": _schema({"root": {"type": "string"}}),
        },
        {
            "name": "p2p_registry_show",
            "description": "Show a generated P2P registry.",
            "inputSchema": _schema({"root": {"type": "string"}, "name": {"type": "string"}}, ["name"]),
        },
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
    if name == "p2p_work_status":
        return {"work": _to_jsonable(workspace.work_summaries())}
    if name == "p2p_registry_show":
        return {"registry": _to_jsonable(workspace.show_registry(_required(arguments, "name")))}

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
