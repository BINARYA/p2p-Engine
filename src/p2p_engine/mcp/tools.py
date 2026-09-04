from __future__ import annotations

from pathlib import Path
from typing import Any

from p2p_engine.core.project_replication import EntityPrecondition
from p2p_engine.mcp.catalog.common import is_domain_mutation
from p2p_engine.mcp.handlers.collaboration import handle_collaboration_tool
from p2p_engine.mcp.handlers.maintenance import handle_maintenance_tool
from p2p_engine.mcp.handlers.project import handle_project_tool
from p2p_engine.mcp.handlers.project_readiness import handle_project_readiness_tool
from p2p_engine.mcp.handlers.proposals import handle_proposal_tool
from p2p_engine.mcp.handlers.vertical_registry import handle_vertical_registry_tool
from p2p_engine.mcp.handlers.work_specs import handle_work_spec_tool
from p2p_engine.mcp.registry import TOOL_NAMES as TOOL_NAMES
from p2p_engine.mcp.registry import tool_definitions
from p2p_engine.services.project_application import open_project_application


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, object]:
    arguments = arguments or {}
    root = Path(str(arguments.get("root") or Path.cwd()))
    workspace = open_project_application(root)
    definitions = {item["name"]: item for item in tool_definitions()}
    definition = definitions.get(name)
    if definition is None:
        raise ValueError(f"Unknown MCP tool: {name}")
    binding = workspace.adapter.linked_replicas.load()
    if binding is not None and name not in {
        "p2p_linked_replica_status",
        "p2p_linked_replica_catch_up",
        "p2p_project_lifecycle_status",
        "p2p_project_lifecycle_preview",
        "p2p_project_publication_list",
    }:
        description = str(definition.get("description") or "")
        if is_domain_mutation(name, description):
            operation_id = str(arguments.get("linked_operation_id") or "")
            expected = arguments.get("linked_expected_project_revision")
            if not operation_id or isinstance(expected, bool) or not isinstance(expected, int):
                raise ValueError(
                    "P2P_REPLICATION_PRECONDITION_REQUIRED: linked mutation requires "
                    "linked_operation_id and linked_expected_project_revision"
                )
            raw_preconditions = arguments.get("linked_entity_preconditions", [])
            if not isinstance(raw_preconditions, list):
                raise ValueError(
                    "P2P_REPLICATION_INVALID: linked_entity_preconditions must be an array"
                )
            preconditions: list[EntityPrecondition] = []
            for item in raw_preconditions:
                if not isinstance(item, dict) or set(item) != {
                    "kind",
                    "id",
                    "expected_version",
                }:
                    raise ValueError(
                        "P2P_REPLICATION_INVALID: linked entity precondition fields differ"
                    )
                preconditions.append(
                    EntityPrecondition(
                        str(item["kind"]),
                        str(item["id"]),
                        item["expected_version"],
                    )
                )
            excluded = {
                "root",
                "linked_operation_id",
                "linked_expected_project_revision",
                "linked_entity_preconditions",
                "actor",
                "actor_id",
                "executor",
                "executor_id",
                "executor_kind",
                "authority_context",
            }
            payload = {
                key: value for key, value in arguments.items() if key not in excluded
            }
            linked = workspace.linked_replica_submit_command(
                operation_id=operation_id,
                idempotency_key=operation_id,
                command=name.removeprefix("p2p_").replace("_", "."),
                payload_contract="p2p-linked-mcp-command/v1",
                payload=payload,
                expected_project_revision=expected,
                entity_preconditions=tuple(preconditions),
            )
            raw_receipt = linked.get("receipt")
            completed = (
                isinstance(raw_receipt, dict)
                and raw_receipt.get("status") == "completed"
            )
            return {"linked_operation": linked, "mutation_performed": completed}
        freshness = workspace.linked_replica_before_operation(mutation=False)
    else:
        freshness = None
    handled = handle_maintenance_tool(workspace, name, arguments)
    if handled is not None:
        return _with_freshness(handled, freshness)
    handled = handle_project_tool(workspace, name, arguments)
    if handled is not None:
        return _with_freshness(handled, freshness)
    handled = handle_project_readiness_tool(workspace, name, arguments)
    if handled is not None:
        return _with_freshness(handled, freshness)
    handled = handle_vertical_registry_tool(name, arguments)
    if handled is not None:
        return _with_freshness(handled, freshness)
    handled = handle_proposal_tool(workspace, name, arguments)
    if handled is not None:
        return _with_freshness(handled, freshness)
    handled = handle_collaboration_tool(workspace, name, arguments)
    if handled is not None:
        return _with_freshness(handled, freshness)
    handled = handle_work_spec_tool(workspace, name, arguments)
    if handled is not None:
        return _with_freshness(handled, freshness)

    raise ValueError(f"Unknown MCP tool: {name}")


def _with_freshness(
    payload: dict[str, object], freshness: object | None
) -> dict[str, object]:
    if freshness is None:
        return payload
    result = dict(payload)
    to_dict = getattr(freshness, "to_dict", None)
    if callable(to_dict):
        result["linked_replica_freshness"] = to_dict()
    return result
