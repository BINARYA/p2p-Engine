# P2PWorkspace Project Initialization Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract `P2PWorkspace.init_project()` bootstrap behavior into a dedicated
runtime service while preserving CLI, MCP, and direct workspace compatibility.

## Requirements

- [x] R001: `P2PWorkspace.init_project()` must keep the same signature, return
  type, created-path ordering semantics, and idempotent file creation behavior.

- [x] R002: Initialization must continue creating the same project metadata,
  governance placeholders, templates, readiness profile, domain state, rubrics,
  permissions policy, proposals/prompts directories, remote profile, and agent
  instruction files.

- [x] R003: Domain behavior must remain compatible: unresolved domains create
  `next-actions.yml`, template domains do not, and rubrics/domain payloads stay
  unchanged.

- [x] R004: Repository/remote behavior must remain compatible for local and
  remote/cloud modes, including validation errors for ambiguous remote aliases.

- [x] R005: Owner permissions and default agent instruction setup must keep the
  same payloads and generated files.

- [x] R006: The initialization service must not import Typer, Rich, MCP,
  JSON-RPC, Git/sync, branch lifecycle, validation, registry generation,
  proposal lifecycle, maturity computation, or CLI formatting.

- [x] R007: Existing CLI, MCP, and direct workspace initialization tests must
  remain compatible.

## Non-Goals

- Changing bootstrap file contents.
- Changing project domain templates or rubrics.
- Changing agent instruction generation behavior.
- Changing remote profile semantics.
- Editing `.p2p/` managed project state by hand.
