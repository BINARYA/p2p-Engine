# Design - MCP Tool Surface

## Requirements Covered

- R001, R002, R003, R004, R005

## Key Decisions

- D001: MCP tools dispatch to `P2PWorkspace` methods.
  Rationale: CLI and MCP share deterministic behavior.

- D002: Consent receipts gate owner-sensitive operations.
  Rationale: local MCP actor identity is not strong authentication by itself.

## Components

- `src/p2p_engine/mcp/server.py`
  - stdio MCP server entrypoint.
- `src/p2p_engine/mcp/tools.py`
  - tool definitions, schemas, and dispatch.
- `src/p2p_engine/storage/filesystem.py`
  - shared workspace behavior.
- `tests/test_mcp.py`
  - comprehensive MCP behavior tests.

## Evidence

- Tool registry and definitions: `src/p2p_engine/mcp/tools.py:15`,
  `src/p2p_engine/mcp/tools.py:120`, `src/p2p_engine/mcp/tools.py:977`.
- Dispatch: `src/p2p_engine/mcp/tools.py:1093`,
  `src/p2p_engine/mcp/tools.py:1856`.
- Server entrypoint: `src/p2p_engine/mcp/server.py:15`.
- Tests: `tests/test_mcp.py:46`, `tests/test_mcp.py:1045`,
  `tests/test_mcp.py:1081`, `tests/test_mcp.py:1498`,
  `tests/test_mcp.py:1589`.

## Risks

- Tool coverage can drift from CLI coverage unless tests assert both surfaces.
