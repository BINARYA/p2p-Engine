# MCP Registry Domain Catalog Split Requirements

## Purpose

Split the large MCP tool registry catalog into domain-specific definition
modules while preserving the public MCP tool surface exactly.

This is a local development feature for runtime refactoring. It does not change
P2P governance behavior and does not edit `.p2p/` state.

## Requirements

- R001: Preserve `p2p_engine.mcp.registry.tool_definitions()` as the public
  function used by the MCP server.
- R002: Preserve `p2p_engine.mcp.registry.TOOL_NAMES` as the public ordered list
  of supported MCP tools.
- R003: Preserve every existing MCP tool name, description, input schema,
  required field list, enum value, default-free schema shape, and list order.
- R004: Move MCP tool definitions into cohesive domain catalog modules without
  moving runtime execution handlers.
- R005: Keep `mcp/tools.py` as the minimal dispatch facade and keep
  `mcp/handlers/*` as execution handlers.
- R006: Add regression tests that compare the tool catalog before and after the
  split through public APIs rather than private implementation details.
- R007: Do not introduce dynamic discovery or filesystem scanning for MCP tool
  definitions. The registry must remain deterministic and import-time explicit.
- R008: Do not change permission semantics, write-safe/read-only descriptions,
  or consent-related wording while moving definitions.

## Non-Goals

- This feature does not add new MCP tools.
- This feature does not change MCP handler behavior.
- This feature does not rename tools or reorganize CLI commands.
- This feature does not change P2P proposal, Work, sync, or consent behavior.
