# P2PWorkspace Facade Final Reassessment Requirements

## Purpose

This local development feature reassesses the refactored runtime surfaces after
the service and helper extraction sequence. It does not change P2P governance
state and does not define product behavior.

## Requirements

- R001: Reassess `src/p2p_engine/storage/filesystem.py`,
  `src/p2p_engine/cli.py`, CLI command modules, `src/p2p_engine/mcp/tools.py`,
  `src/p2p_engine/mcp/registry.py`, and MCP handlers after the completed helper
  consolidation work.
- R002: Classify each remaining large module as one of:
  compatibility facade, composition root, schema/catalog registry,
  presentation module, service module, or extraction candidate.
- R003: Do not extract code only to reduce line count. A new extraction must
  improve ownership, testability, compatibility safety, or future change
  isolation.
- R004: Preserve public CLI command names, option semantics, output behavior,
  MCP tool names, MCP schemas, `P2PWorkspace` facade methods, and `.p2p`
  storage behavior.
- R005: Produce an explicit task checklist before any further runtime refactor
  starts, so progress can be followed step by step.
- R006: Update the local refactoring tracker with the reassessment result and
  the next recommended implementation feature.

## Non-Goals

- This feature does not mutate `.p2p/` state.
- This feature does not introduce new P2P Engine behavior.
- This feature does not split runtime modules unless the reassessment identifies
  a focused follow-up feature with its own requirements, design, and tasks.
