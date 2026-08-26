from __future__ import annotations

from pathlib import Path
from typing import Any

from p2p_engine.core.vertical_registry import VERTICAL_REGISTRY_PROTOCOL_VERSION
from p2p_engine.mcp.handlers.common import required, to_jsonable
from p2p_engine.services.vertical_catalog import VerticalCatalogService
from p2p_engine.services.vertical_registry import VerticalRegistryClient


def handle_vertical_registry_tool(
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_vertical_domain_list":
        domains, page = VerticalRegistryClient().list_domains_with_page(
            _optional_text(arguments, "registry"),
            include_private=bool(arguments.get("include_private") or False),
        )
        return {
            "vertical_domains": _versioned_items(domains, page),
            "mutation_performed": False,
            "network_access": "remote_read",
        }
    if name == "p2p_vertical_domain_search":
        domains, page = VerticalRegistryClient().list_domains_with_page(
            _optional_text(arguments, "registry"),
            query=required(arguments, "query"),
            include_private=bool(arguments.get("include_private") or False),
        )
        return {
            "vertical_domains": _versioned_items(domains, page),
            "mutation_performed": False,
            "network_access": "remote_read",
        }
    if name == "p2p_vertical_domain_inspect":
        domain = VerticalRegistryClient().domain(
            required(arguments, "domain_id"),
            _optional_text(arguments, "registry"),
            include_private=bool(arguments.get("include_private") or False),
        )
        return {
            "vertical_domain": {
                "protocol_version": VERTICAL_REGISTRY_PROTOCOL_VERSION,
                "domain": to_jsonable(domain),
            },
            "mutation_performed": False,
            "network_access": "remote_read",
        }
    if name == "p2p_vertical_release_list":
        items, page = VerticalCatalogService(
            Path(str(arguments.get("root") or Path.cwd())),
            client=VerticalRegistryClient(),
        ).remote_items_with_page(
            registry=_optional_text(arguments, "registry"),
            domain=_optional_text(arguments, "domain"),
            include_private=bool(arguments.get("include_private") or False),
        )
        return {
            "vertical_releases": _versioned_items(items, page),
            "mutation_performed": False,
            "network_access": "remote_read",
        }
    if name == "p2p_vertical_release_search":
        items, page = VerticalCatalogService(
            Path(str(arguments.get("root") or Path.cwd())),
            client=VerticalRegistryClient(),
        ).remote_items_with_page(
            registry=_optional_text(arguments, "registry"),
            query=required(arguments, "query"),
            domain=_optional_text(arguments, "domain"),
            include_private=bool(arguments.get("include_private") or False),
        )
        return {
            "vertical_releases": _versioned_items(items, page),
            "mutation_performed": False,
            "network_access": "remote_read",
        }
    return None


def _optional_text(arguments: dict[str, Any], key: str) -> str:
    return str(arguments.get(key) or "").strip()


def _versioned_items(items: tuple[object, ...], page: object) -> dict[str, object]:
    return {
        "protocol_version": VERTICAL_REGISTRY_PROTOCOL_VERSION,
        "items": to_jsonable(items),
        "page": to_jsonable(page),
    }
