# MCP Consent Audit Helper Extraction Requirements

## Goal

Extract consent audit helper behavior from `src/p2p_engine/mcp/tools.py` into a
small MCP-local helper module without changing MCP tool names, schemas, payload
shapes, consent semantics, Git side effects, or `P2PWorkspace` public APIs.

## Functional Requirements

- Preserve consent validation and consumption behavior for all permission-gated
  MCP tools.
- Preserve audit commit message format:
  `P2P consent consume CONSENT-XXX`.
- Preserve optional audit push behavior when a remote and branch are supplied.
- Preserve used-with-error marking when an operation moves Git HEAD and then
  fails.
- Preserve sync consent target formatting as `{remote}/{branch}`.
- Preserve detached HEAD guard for sync consent target resolution.
- Keep MCP schemas, tool registry entries, dispatch branches, and JSON response
  shapes in `mcp/tools.py`.

## Boundary Requirements

- New helper code may live under `src/p2p_engine/mcp/`.
- The helper module may depend on `P2PWorkspace` and Git adapter functions.
- The helper module must not define MCP tool schemas or dispatch routing.
- The helper module must not own domain lifecycle behavior for proposals, sync,
  consent storage, or Work.
- `mcp/tools.py` remains the compatibility presentation/transport surface until
  the later MCP registry/tool handler split.

## Compatibility Requirements

- Existing MCP tests for consent-gated sync, proposal publish/request-review,
  governance decisions, branch accept/reject/merge/finalize/cleanup, and read
  tools must continue to pass unchanged.
- Full test suite and `.venv/bin/p2p validate` must pass after extraction.
