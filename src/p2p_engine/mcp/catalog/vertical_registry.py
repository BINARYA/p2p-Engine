from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            "p2p_vertical_domain_list",
            (
                "Read-only remote network read: list advisory vertical-registry "
                "domains from an explicitly selected or configured registry. "
                "Does not mutate project state, pull artifacts, initialize a project, "
                "write the artifact cache, or infer structure compatibility."
            ),
            {
                "root": {"type": "string"},
                "registry": {"type": "string"},
                "include_private": {"type": "boolean"},
            },
        ),
        _tool(
            "p2p_vertical_domain_search",
            (
                "Read-only remote network read: search advisory vertical-registry "
                "domains. Recommendations are metadata only and never trigger pull "
                "or project initialization. Does not mutate project state."
            ),
            {
                "root": {"type": "string"},
                "query": {"type": "string"},
                "registry": {"type": "string"},
                "include_private": {"type": "boolean"},
            },
            ["query"],
        ),
        _tool(
            "p2p_vertical_domain_inspect",
            (
                "Read-only remote network read: inspect one advisory catalog domain "
                "by exact external ID without enumerating inaccessible private domains "
                "or changing project structure. Does not mutate project state."
            ),
            {
                "root": {"type": "string"},
                "domain_id": {"type": "string"},
                "registry": {"type": "string"},
                "include_private": {"type": "boolean"},
            },
            ["domain_id"],
        ),
        _tool(
            "p2p_vertical_release_list",
            (
                "Read-only remote network read: list remote vertical releases, "
                "optionally filtered by one exact advisory domain external ID. "
                "Does not download artifacts or write the user cache."
            ),
            {
                "root": {"type": "string"},
                "registry": {"type": "string"},
                "domain": {"type": "string"},
                "include_private": {"type": "boolean"},
            },
        ),
        _tool(
            "p2p_vertical_release_search",
            (
                "Read-only remote network read: search remote vertical releases, "
                "optionally filtered by one exact advisory domain external ID. "
                "Domain matches do not prove semantic compatibility. Does not "
                "mutate project state."
            ),
            {
                "root": {"type": "string"},
                "query": {"type": "string"},
                "registry": {"type": "string"},
                "domain": {"type": "string"},
                "include_private": {"type": "boolean"},
            },
            ["query"],
        ),
    ]
