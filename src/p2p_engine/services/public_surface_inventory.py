from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from p2p_engine.services.agent_capabilities import (
    AGENT_CAPABILITIES,
    AGENT_CAPABILITY_CATALOG_VERSION,
    AgentCapability,
)


PUBLIC_SURFACE_CONTRACT_VERSION = "p2p-public-surfaces-v1"


@dataclass(frozen=True)
class PublicSurfaceIssue:
    code: str
    capability_id: str
    target: str
    message: str


@dataclass(frozen=True)
class PublicSurfaceSnapshot:
    contract_version: str
    capability_catalog_version: str
    cli_paths: tuple[str, ...]
    mcp_tools: tuple[str, ...]
    capabilities: tuple[AgentCapability, ...]
    semantic_sha256: str
    issues: tuple[PublicSurfaceIssue, ...]


def cli_leaf_paths(command: Any, *, root_name: str = "p2p") -> tuple[str, ...]:
    paths: list[str] = []

    def visit(current: Any, prefix: tuple[str, ...]) -> None:
        commands = getattr(current, "commands", None)
        if isinstance(commands, dict) and commands:
            if bool(getattr(current, "invoke_without_command", False)) and len(prefix) > 1:
                paths.append(" ".join(prefix))
            for name, child in sorted(commands.items()):
                visit(child, (*prefix, str(name)))
            return
        if len(prefix) > 1:
            paths.append(" ".join(prefix))

    visit(command, (root_name,))
    return tuple(sorted(set(paths)))


def validate_capabilities(
    cli_paths: Iterable[str],
    mcp_tools: Iterable[str],
    capabilities: Iterable[AgentCapability] = AGENT_CAPABILITIES,
) -> tuple[PublicSurfaceIssue, ...]:
    registered_cli = set(cli_paths)
    registered_mcp = set(mcp_tools)
    issues: list[PublicSurfaceIssue] = []
    seen_capabilities: set[str] = set()
    for capability in capabilities:
        if capability.capability_id in seen_capabilities:
            issues.append(
                PublicSurfaceIssue(
                    code="P2P_SURFACE_DUPLICATE_CAPABILITY",
                    capability_id=capability.capability_id,
                    target=capability.capability_id,
                    message=f"Duplicate agent capability: {capability.capability_id}.",
                )
            )
        seen_capabilities.add(capability.capability_id)
        if not capability.cli_paths and not capability.mcp_tools:
            issues.append(
                PublicSurfaceIssue(
                    code="P2P_SURFACE_EMPTY_CAPABILITY",
                    capability_id=capability.capability_id,
                    target=capability.capability_id,
                    message=f"Agent capability has no registered surface: {capability.capability_id}.",
                )
            )
        for path in capability.cli_paths:
            if path not in registered_cli:
                issues.append(
                    PublicSurfaceIssue(
                        code="P2P_SURFACE_UNKNOWN_CLI_PATH",
                        capability_id=capability.capability_id,
                        target=path,
                        message=f"Capability {capability.capability_id} references unknown CLI path: {path}.",
                    )
                )
        for name in capability.mcp_tools:
            if name not in registered_mcp:
                issues.append(
                    PublicSurfaceIssue(
                        code="P2P_SURFACE_UNKNOWN_MCP_TOOL",
                        capability_id=capability.capability_id,
                        target=name,
                        message=f"Capability {capability.capability_id} references unknown MCP tool: {name}.",
                    )
                )
    return tuple(issues)


def public_surface_snapshot() -> PublicSurfaceSnapshot:
    from typer.main import get_command

    from p2p_engine.cli import app
    from p2p_engine.mcp.registry import TOOL_NAMES

    cli_paths = cli_leaf_paths(get_command(app))
    mcp_tools = tuple(sorted(TOOL_NAMES))
    capabilities = tuple(AGENT_CAPABILITIES)
    issues = validate_capabilities(cli_paths, mcp_tools, capabilities)
    semantic_payload = {
        "contract_version": PUBLIC_SURFACE_CONTRACT_VERSION,
        "capability_catalog_version": AGENT_CAPABILITY_CATALOG_VERSION,
        "cli_paths": cli_paths,
        "mcp_tools": mcp_tools,
        "capabilities": [asdict(capability) for capability in capabilities],
    }
    semantic_sha256 = hashlib.sha256(
        json.dumps(semantic_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return PublicSurfaceSnapshot(
        contract_version=PUBLIC_SURFACE_CONTRACT_VERSION,
        capability_catalog_version=AGENT_CAPABILITY_CATALOG_VERSION,
        cli_paths=cli_paths,
        mcp_tools=mcp_tools,
        capabilities=capabilities,
        semantic_sha256=semantic_sha256,
        issues=issues,
    )
