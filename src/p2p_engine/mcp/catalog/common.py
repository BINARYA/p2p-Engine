from __future__ import annotations


def schema(properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def tool(
    name: str,
    description: str,
    properties: dict[str, object],
    required: list[str] | None = None,
) -> dict[str, object]:
    effective_properties = dict(properties)
    if is_domain_mutation(name, description):
        effective_properties.update(
            {
                "linked_operation_id": {
                    "type": "string",
                    "description": (
                        "Required only for a linked-local mutation; reuse it for recovery."
                    ),
                },
                "linked_expected_project_revision": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Revision observed when linked work was prepared.",
                },
                "linked_entity_preconditions": {
                    "type": "array",
                    "maxItems": 4096,
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string"},
                            "id": {"type": "string"},
                            "expected_version": {"type": "integer", "minimum": 0},
                        },
                        "required": ["kind", "id", "expected_version"],
                        "additionalProperties": False,
                    },
                },
            }
        )
    return {
        "name": name,
        "description": description,
        "inputSchema": schema(effective_properties, required),
    }


def is_domain_mutation(name: str, description: str) -> bool:
    """Fail-closed catalog classification used by linked-local MCP routing."""
    lowered = description.lower()
    if any(
        marker in lowered
        for marker in (
            "write-safe",
            "classification mutation",
            "metadata update",
            "permission-gated decision apply",
            "permission-gated apply",
            "consent-gated receipt-backed",
        )
    ):
        return True
    # These convenience tools return previews; they do not perform the named
    # decision and must remain local read/preparation operations.
    if name in {"p2p_proposal_accept", "p2p_proposal_reject", "p2p_proposal_defer"}:
        return False
    return False
