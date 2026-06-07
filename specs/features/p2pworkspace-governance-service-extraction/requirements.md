# P2PWorkspace Governance Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract governance bootstrap, governance status, proposal vote tracking, and
decision precedent recording from `P2PWorkspace` into a dedicated runtime
service while preserving CLI and direct workspace compatibility.

## Requirements

- [x] R001: `P2PWorkspace.init_governance()` must keep the same signature,
  return type, governance mode validation, file paths, and overwrite behavior.

- [x] R002: `P2PWorkspace.governance_status()` must keep reporting the same
  mode, role count, precedent count, and relative governance file path.

- [x] R003: `P2PWorkspace.record_vote()` and `vote_status()` must preserve
  `votes.yml` shape, vote append behavior, count calculation, winner/tie
  semantics, and validation errors for malformed vote files.

- [x] R004: `P2PWorkspace.record_precedent()` must preserve proposal existence
  validation, precedent id sequencing, payload shape, and relative return path.

- [x] R005: Existing collaboration CLI behavior must continue working through
  the same workspace facade methods.

- [x] R006: The governance service must not import Typer, Rich, MCP, JSON-RPC,
  Git/sync, branch lifecycle, registry generation, project initialization, or
  CLI formatting.

## Non-Goals

- Changing governance policy semantics.
- Changing proposal decision service behavior.
- Changing managed P2P governance state by hand.
- Adding new governance modes.
