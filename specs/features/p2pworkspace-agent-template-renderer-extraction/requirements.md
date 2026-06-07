# P2PWorkspace Agent Template Renderer Extraction Requirements

## Status

Implemented and verified.

## Goal

Move agent adapter constants, profile normalization, policy payload generation,
file mapping, and generated instruction template renderers out of
`storage/filesystem.py` into a dedicated service-side module.

## Requirements

- [x] R001: Generated AGENTS, Codex, Claude, Cursor, Copilot, Gemini, shared
  skill, and agent policy content must remain byte-for-byte compatible.

- [x] R002: Agent adapter IDs, aliases, `all` expansion, capabilities, file map
  template IDs, and shared-file ownership semantics must remain unchanged.

- [x] R003: `P2PWorkspace.init_project()` and `AgentInstructionService` must keep
  using the same public behavior after renderer relocation.

- [x] R004: The renderer module must not import `P2PWorkspace`, Typer, Rich, MCP,
  JSON-RPC, Git/sync, branch lifecycle, validation, registry generation,
  proposal lifecycle, or maturity behavior.

- [x] R005: Existing CLI, MCP, and direct agent service tests must remain
  compatible.

## Non-Goals

- Changing generated instruction text.
- Changing agent orchestration, drift detection, install/update/uninstall
  behavior.
- Changing project initialization beyond import wiring.
- Editing `.p2p/` managed project state by hand.
