# P2PWorkspace Dead Filesystem Helper Cleanup Requirements

## Goal

Remove low-level helper functions and constants from `storage.filesystem` that
are no longer called after service extraction.

## Requirements

- Remove only helpers proven unused by `rg`.
- Keep helpers still used by the compatibility facade:
  - YAML read/write helpers;
  - identity slug for proposal draft commit service wiring;
  - duplicate proposal id formatting;
  - review request suggestion URL helpers.
- Preserve public CLI, MCP, and service behavior.
- Do not edit `.p2p/` governance state by hand.

## Non-Goals

- Do not extract new behavior.
- Do not change proposal, permission, consent, Work branch, or proposal branch
  semantics.
- Do not remove compatibility facade methods.
