from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest

from p2p_engine.services.agent_capabilities import AGENT_CAPABILITIES
from p2p_engine.services.agent_templates import agent_instruction_files
from p2p_engine.services.public_surface_inventory import (
    PUBLIC_SURFACE_CONTRACT_VERSION,
    public_surface_snapshot,
    validate_capabilities,
)


@pytest.mark.unit
def test_public_surface_inventory_derives_registered_cli_and_mcp_surfaces() -> None:
    snapshot = public_surface_snapshot()

    assert snapshot.contract_version == PUBLIC_SURFACE_CONTRACT_VERSION
    assert len(snapshot.cli_paths) == 279
    assert len(snapshot.mcp_tools) == 179
    assert "p2p vertical registry list" in snapshot.cli_paths
    assert "p2p vertical draft publish" in snapshot.cli_paths
    assert "p2p project authority capabilities" in snapshot.cli_paths
    assert "p2p project authority rotate apply" in snapshot.cli_paths
    assert "p2p project domain set" in snapshot.cli_paths
    assert "p2p project structure add-section" in snapshot.cli_paths
    assert "p2p project memory classification" in snapshot.cli_paths
    assert "p2p proposal scope set" in snapshot.cli_paths
    assert "p2p_project_vertical_list" in snapshot.mcp_tools
    assert "p2p_project_domain_set" in snapshot.mcp_tools
    assert "p2p_project_structure_add_section" in snapshot.mcp_tools
    assert "p2p_project_memory_classification" in snapshot.mcp_tools
    assert "p2p_proposal_scope_show" in snapshot.mcp_tools
    assert "p2p_proposal_scope_set" in snapshot.mcp_tools
    assert len(snapshot.semantic_sha256) == 64
    assert snapshot.issues == ()


@pytest.mark.unit
def test_public_surface_inventory_rejects_unregistered_capability_targets() -> None:
    invalid = replace(
        AGENT_CAPABILITIES[0],
        capability_id="invalid.example",
        cli_paths=("p2p removed command",),
        mcp_tools=("p2p_removed_tool",),
    )

    issues = validate_capabilities(
        ("p2p status",),
        ("p2p_project_status",),
        (invalid,),
    )

    assert {issue.code for issue in issues} == {
        "P2P_SURFACE_UNKNOWN_CLI_PATH",
        "P2P_SURFACE_UNKNOWN_MCP_TOOL",
    }


@pytest.mark.unit
def test_public_surface_inventory_is_deterministic() -> None:
    first = public_surface_snapshot()
    second = public_surface_snapshot()

    assert second.cli_paths == first.cli_paths
    assert second.mcp_tools == first.mcp_tools
    assert second.semantic_sha256 == first.semantic_sha256


@pytest.mark.unit
def test_current_agent_template_command_and_tool_references_are_registered() -> None:
    snapshot = public_surface_snapshot()
    rendered = agent_instruction_files(
        "Surface Project",
        ["generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode"],
        "local",
    )
    command_references: set[str] = set()
    tool_references: set[str] = set()
    non_tool_policy_terms = {
        "p2p_canonical",
        "p2p_cli_or_explicit_mcp_write_tool",
        "p2p_export_or_repository_output",
        "p2p_generate_or_import_primitive",
        "p2p_generated_narrative",
        "p2p_import_primitive",
        "p2p_imported_artifact",
    }
    for content in rendered.values():
        command_references.update(re.findall(r"`(p2p [^`\n]+)`", content))
        command_references.update(
            line.strip()
            for line in content.splitlines()
            if line.strip().startswith("p2p ")
        )
        tool_references.update(re.findall(r"`(p2p_[a-z0-9_]+)`", content))

    unresolved_commands = {
        command.rstrip(".,:;")
        for command in command_references
        if not any(
            command.rstrip(".,:;") == path
            or command.rstrip(".,:;").startswith(path + " ")
            for path in snapshot.cli_paths
        )
    }
    unresolved_tools = tool_references - set(snapshot.mcp_tools) - non_tool_policy_terms

    assert command_references
    assert unresolved_commands == set()
    assert unresolved_tools == set()


@pytest.mark.unit
def test_mcp_reference_table_is_checked_against_the_registered_registry() -> None:
    root = Path(__file__).resolve().parents[1]
    mcp_guide = (root / "docs" / "MCP.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"`(p2p_[a-z0-9_]+)`", mcp_guide))

    assert documented == set(public_surface_snapshot().mcp_tools)
