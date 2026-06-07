# P2PWorkspace Registry Record Builder Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract registry record construction helpers from `P2PWorkspace` into a
dedicated service while preserving registry refresh/status/show behavior and all
callbacks used by other services.

## Requirements

- [x] R001: Accepted proposal record construction must preserve accepted-status
  filtering, title cleanup, feature id generation, source paths, problem/goals,
  non-goals, proposal text, and decision text fields.

- [x] R002: Proposal registry records must preserve proposal id/title/status,
  path, summary, decision file, related changes, and source file list fields.

- [x] R003: Decision, change, choice, relation, artifact, and readiness registry
  records must preserve existing payload shapes, ordering, and fallback values.

- [x] R004: Existing services using registry record callbacks must continue to
  receive equivalent data through `P2PWorkspace` facade methods.

- [x] R005: `RegistryService.refresh()`, `registry_status()`, and
  `show_registry()` must continue to produce the same outputs.

- [x] R006: The registry record builder service must not import Typer, Rich,
  MCP, JSON-RPC, Git/sync, branch lifecycle, project initialization, or CLI
  formatting.

## Non-Goals

- Changing registry file schema.
- Changing registry refresh/write behavior.
- Changing readiness computation.
- Changing proposal, change, choice, or work lifecycle behavior.
