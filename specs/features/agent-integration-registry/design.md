# Design - Agent Integration Registry

## Requirements Covered

- R001, R002, R003, R004, R005, R006

## Key Decisions

- D001: Generic is the mandatory baseline adapter.
  Rationale: every agent profile inherits common P2P governance boundaries.

- D002: File drift makes updates conservative by default.
  Rationale: generated files may be edited by humans and must not be overwritten
  silently.

- D003: MCP exposes the same safe lifecycle operations as structured tools.
  Rationale: compatible agents should not parse CLI text or edit files directly.

## Components

- `src/p2p_engine/cli.py`
  - `agent doctor`, `agent list`, `agent show`, `agent install`,
    `agent update`, `agent uninstall`, `agent instructions refresh`.
- `src/p2p_engine/storage/filesystem.py`
  - registry construction, adapter files, drift detection, safe uninstall,
    generated instruction content.
- `src/p2p_engine/mcp/tools.py`
  - `p2p_agent_*` tools.
- `tests/test_cli.py`, `tests/test_mcp.py`
  - init, registry, drift, MCP lifecycle.

## Evidence

- CLI definitions: `src/p2p_engine/cli.py:120`, `src/p2p_engine/cli.py:392`,
  `src/p2p_engine/cli.py:430`, `src/p2p_engine/cli.py:444`,
  `src/p2p_engine/cli.py:465`, `src/p2p_engine/cli.py:480`,
  `src/p2p_engine/cli.py:493`.
- Storage behavior: `src/p2p_engine/storage/filesystem.py:824`,
  `src/p2p_engine/storage/filesystem.py:880`,
  `src/p2p_engine/storage/filesystem.py:904`,
  `src/p2p_engine/storage/filesystem.py:1013`,
  `src/p2p_engine/storage/filesystem.py:7050`,
  `src/p2p_engine/storage/filesystem.py:7466`.
- MCP tools: `src/p2p_engine/mcp/tools.py:15`,
  `src/p2p_engine/mcp/tools.py:181`, `src/p2p_engine/mcp/tools.py:1100`.
- Tests: `tests/test_cli.py:951`, `tests/test_cli.py:987`,
  `tests/test_cli.py:998`, `tests/test_cli.py:1026`,
  `tests/test_mcp.py:1081`.

## Risks

- Generated instruction templates are product behavior; future local-only
  development rules must not leak into released templates unless intentionally
  accepted.
