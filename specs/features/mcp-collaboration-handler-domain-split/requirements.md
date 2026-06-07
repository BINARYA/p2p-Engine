# MCP Collaboration Handler Domain Split Requirements

## Purpose

Split the remaining large MCP collaboration handler into focused handler modules
without changing MCP tool behavior, payloads, permission gates, consent audit
semantics, or public imports.

This is a local development feature. It does not mutate `.p2p/` state.

## Requirements

- R001: Keep `p2p_engine.mcp.handlers.collaboration.handle_collaboration_tool`
  as the public MCP collaboration handler entry point.
- R002: Preserve behavior for remote profile, permissions, consent, sync, and
  proposal branch lifecycle tools.
- R003: Preserve all permission-gated consent validation, error marking,
  consent consumption, audit commit, and push behavior.
- R004: Split implementation by operational domain instead of line count:
  remote/permission/consent, sync, and proposal branch collaboration.
- R005: Do not change `mcp.tools.call_tool()` routing or MCP catalog schemas.
- R006: Add or preserve tests proving unknown tools still return `None` and the
  main collaboration tool families still route through the public entry point.
- R007: Update the refactoring tracker with the new module ownership and
  verification evidence.

## Non-Goals

- This feature does not add new MCP tools.
- This feature does not change managed Git behavior.
- This feature does not change consent receipt data models.
- This feature does not split CLI command modules.
