# P2PWorkspace Agent Instructions Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract agent instruction and integration orchestration from `P2PWorkspace`
into a cohesive runtime service while preserving CLI, MCP, and project
initialization compatibility.

## Requirements

- [x] R001: `P2PWorkspace.refresh_agent_instructions()`,
  `agent_integrations_list()`, `agent_integration_show()`,
  `install_agent_integrations()`, and `uninstall_agent_integration()` must keep
  their public behavior and return shapes.

- [x] R002: `AgentInstructionsResult` and `AgentIntegrationResult` must remain
  import-compatible from `p2p_engine.storage.filesystem`.

- [x] R003: Generated instruction files, agent policy YAML, agent integration
  registry, file hashes, drift states, and shared-file behavior must remain
  compatible.

- [x] R004: `init_project()` must continue creating default agent instructions
  through the facade without owning agent template generation.

- [x] R005: The service must preserve adapter normalization, `all` expansion,
  install/update force behavior, uninstall safeguards, and generic baseline
  behavior.

- [x] R006: The service must not import Typer, Rich, MCP handlers, JSON-RPC,
  Git/sync, branch lifecycle services, validation, registry generation,
  proposal lifecycle, or project maturity.

- [x] R007: Existing CLI and MCP agent commands must remain compatible.

- [x] R008: Template renderers may remain as compatibility helpers in
  `filesystem.py` for this slice, provided runtime orchestration and registry
  behavior no longer live there.

## Non-Goals

- Changing the generated instruction text.
- Fully extracting agent template text renderers.
- Changing agent adapter inventory.
- Changing project initialization beyond delegating agent behavior.
- Editing `.p2p/` managed project state by hand.
