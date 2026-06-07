# P2PWorkspace Conflict Memory Service Extraction Requirements

## Purpose

Extract project conflict-memory behavior from `P2PWorkspace` into a cohesive
service while preserving the existing CLI, MCP, project-refresh, and registry
behavior.

This is local software-development planning. It is not P2P governance state.

## Current Behavior To Preserve

- `p2p conflict record` validates at least two proposals, validates that each
  proposal exists, optionally validates that the winner is one of the listed
  proposals, writes `.p2p/project/conflicts.yml`, and returns conflict status.
- `p2p conflict status` reads `.p2p/project/conflicts.yml` and reports only
  dictionary conflict records.
- MCP `p2p_conflict_status` remains read-only and returns the same JSON shape.
- Conflict records remain advisory project memory. They do not reject,
  supersede, merge, or decide proposals.

## Functional Requirements

1. The service MUST own conflict file path resolution, read/write behavior,
   conflict ID allocation, conflict append behavior, and status normalization.
2. The service MUST keep the `.p2p/project/conflicts.yml` layout unchanged.
3. The service MUST preserve existing validation messages for invalid proposal
   counts, missing proposals, invalid winners, and invalid conflict list shape.
4. The service MUST preserve `recorded_on` date behavior.
5. The service MUST avoid direct CLI and MCP imports.
6. `P2PWorkspace` MUST remain the compatibility facade for public callers.

## Compatibility Requirements

- Public method names on `P2PWorkspace` remain:
  `record_conflict` and `conflict_status`.
- Existing imports of `ConflictStatus` from
  `p2p_engine.storage.filesystem` remain valid.
- No CLI command, CLI output, MCP tool name, or MCP response key changes are
  allowed.

## Non-Goals

- Do not redesign conflict analysis imported from proposal impact artifacts.
- Do not create governance decisions from conflicts.
- Do not extract intake, choice, or Change Set lifecycle behavior in this slice.
- Do not change registry generation.

## Acceptance Criteria

- `src/p2p_engine/services/conflicts.py` contains the extracted service and
  `ConflictStatus` model.
- `src/p2p_engine/storage/filesystem.py` delegates conflict public behavior to
  the service and no longer contains inline conflict-memory implementation.
- Existing CLI and MCP conflict tests pass unchanged.
- New service-level tests cover empty status, record lifecycle, winner
  validation, proposal count validation, and invalid payload handling.
