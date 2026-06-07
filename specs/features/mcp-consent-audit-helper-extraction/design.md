# MCP Consent Audit Helper Extraction Design

## Current Behavior

`src/p2p_engine/mcp/tools.py` currently combines:

- MCP tool registry and JSON schemas;
- dispatch branches for each tool;
- JSON conversion;
- permission-gated operation orchestration;
- consent audit helper functions;
- Git HEAD and audit commit/push helpers.

The consent audit helpers are cohesive enough to move before splitting the full
MCP registry and handlers.

## Target Boundary

Create `src/p2p_engine/mcp/consent_audit.py`.

The module owns:

- `safe_head`;
- `sync_consent_target`;
- `consume_consent_with_audit`;
- `commit_and_push_consent_audit`;
- `mark_consent_error_on_head_change`.

The module does not own:

- MCP tool definitions;
- MCP input schemas;
- MCP dispatch branching;
- JSON payload rendering;
- consent validation call sites;
- proposal/sync/domain operation execution.

## Extraction Strategy

1. Add the helper module with behavior copied from existing private helpers.
2. Import the helpers in `mcp/tools.py` under private aliases matching current
   call sites, or update call sites directly.
3. Remove the helper implementations from `mcp/tools.py`.
4. Add focused tests for helper behavior where current coverage is only through
   broad MCP flows.
5. Run mapped MCP compatibility tests and the full suite.

## Risk Notes

- The biggest compatibility risk is changing when consent is consumed versus
  marked used-with-error.
- Audit commit/push behavior is Git-sensitive and is already asserted in MCP
  tests; those tests must remain unchanged.
- This extraction should not attempt to reduce dispatch duplication. That is a
  later roadmap item.
