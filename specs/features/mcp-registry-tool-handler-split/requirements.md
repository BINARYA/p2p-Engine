# MCP Registry Tool Handler Split Requirements

## Goal

Separate MCP tool registration concerns from runtime tool execution concerns without changing the public MCP tool surface.

## Requirements

- The complete MCP tool name registry must live outside `src/p2p_engine/mcp/tools.py`.
- MCP tool schema definitions must live with the registry, not with runtime dispatch.
- `src/p2p_engine/mcp/tools.py` must remain the compatibility import surface for existing callers.
- `call_tool()` behavior, tool names, tool schemas, and JSON output must remain unchanged.
- Prompt tool kind mapping must remain shared by registry definitions and runtime prompt dispatch.
- The split must be incremental: registry extraction first, handler grouping later.

## Non-Goals

- Do not rename MCP tools.
- Do not change tool input schemas.
- Do not change consent, permission, sync, proposal, or work behavior.
- Do not introduce a new MCP protocol layer.
