# P2PWorkspace Context Packet Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract compact context packet assembly from `P2PWorkspace` into a dedicated
runtime service while preserving CLI, MCP, and direct workspace compatibility.

## Requirements

- [x] R001: `P2PWorkspace.context_packet()` must keep the same signature,
  return type, budget validation, target normalization, and error behavior.

- [x] R002: Current state counts must preserve validation, registry, project
  state, proposal, choice, change, work, and operational brief semantics.

- [x] R003: Default relevant artifacts must preserve draft proposal, open
  choice, and active change ordering, filtering, path fields, and five-item
  limit.

- [x] R004: Targeted artifacts must preserve supported target prefixes
  `PROP-`, `CHANGE-`, `CHOICE-`, and `WORK-`, including medium-budget summary
  expansion for proposals and changes.

- [x] R005: Allowed commands, bounded next step, notes, and do-not-read guidance
  must remain unchanged.

- [x] R006: CLI and MCP context commands must continue working through the same
  workspace facade method.

- [x] R007: The context packet service must not import Typer, Rich, MCP,
  JSON-RPC, Git/sync, branch lifecycle, project initialization, or CLI
  formatting.

## Non-Goals

- Changing context content policy.
- Changing next-action generation.
- Changing registry refresh behavior.
- Changing CLI/MCP output formatting.
