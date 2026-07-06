# Execution Plan - PROP-088

## Phase 1 - Confirm Scope

- Confirm whether MVP scope is limited to impact and exploration import parity.
- Decide whether clarification import parity is included only as a low-risk
  reuse of the existing clarify import service.
- Choose the MCP input shape: source path, direct content payload, or both.

## Phase 2 - Implement Existing-Import MCP Parity

- Add MCP tool definitions for impact import and exploration import.
- Route handlers through existing P2PWorkspace import services.
- Return structured metadata for imported files.
- Preserve existing YAML validation and missing-source errors.

## Phase 3 - Documentation And Tests

- Update the MCP tool matrix with the new write-safe tools and boundaries.
- Add tests for successful imports, malformed impact YAML, missing sources, and
  unsupported artifact-content updates.
- Run validation and focused MCP/tool tests before recommending acceptance of
  implementation work.

## Exit Criteria

- MCP clients can close impact and exploration artifact gaps without direct
  `.p2p/` writes.
- Unsupported artifact mutations fail clearly.
- Readiness and context see imported artifact content after MCP import.

