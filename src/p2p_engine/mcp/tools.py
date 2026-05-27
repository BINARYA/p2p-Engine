from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from p2p_engine.storage.filesystem import P2PWorkspace


TOOL_NAMES = (
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
