# MCP Collaboration Handler Domain Split Design

## Current Shape

`src/p2p_engine/mcp/handlers/collaboration.py` was approximately 566 lines and
contains:

- remote profile and consent request/status/show handling;
- sync status/fetch/pull/push handling;
- proposal draft commit and proposal branch lifecycle handling;
- permission-gated proposal publish, review, branch accept/reject, merge,
  finalize, and cleanup helpers.

The file is behaviorally correct but still too broad for safe future changes.

## Target Shape

Keep the public handler module as a router:

```text
src/p2p_engine/mcp/handlers/
  collaboration.py             # public router
  collaboration_remote.py      # remote, permissions, consent status/request
  collaboration_sync.py        # sync status/fetch/pull/push
  collaboration_proposals.py   # proposal draft/branch/publish/review/merge flows
```

`collaboration.py` calls each focused handler in order and returns the first
non-`None` result.

## Ownership

- `collaboration_remote.py` owns non-branch project collaboration setup and
  consent read/request tools.
- `collaboration_sync.py` owns sync tools and sync consent target handling
  through existing `mcp.consent_audit` helpers.
- `collaboration_proposals.py` owns proposal branch collaboration tools and
  imports `ProposalMergeConflict`.
- `mcp.handlers.proposals` continues to own `p2p_proposal_branch_scan`, matching
  the pre-existing runtime routing.
- `mcp.consent_audit` remains the shared audit helper module.
- `mcp.handlers.common` remains the argument and JSON conversion helper module.

## Final Shape

After extraction:

| Module | Lines | Responsibility |
| --- | ---: | --- |
| `mcp/handlers/collaboration.py` | 22 | Public router only. |
| `mcp/handlers/collaboration_remote.py` | 56 | Remote profile, permissions, consent request/status/show. |
| `mcp/handlers/collaboration_sync.py` | 86 | Sync status/fetch and permission-gated pull/push. |
| `mcp/handlers/collaboration_proposals.py` | 457 | Proposal draft, branch, publish, review, decision, merge, finalize, cleanup collaboration flows. |

## Compatibility Rules

- The return dictionaries must remain unchanged.
- `handle_collaboration_tool()` must still return `None` for unrelated tools.
- Public imports from `p2p_engine.mcp.handlers.collaboration` must continue to
  work for the public entry function.
- Consent validation must happen before permission-gated operations exactly as
  before.
- Consent error marking must continue to record head changes only when a
  mutation partially happened.

## Verification

Run focused MCP collaboration tests and then the full suite:

```bash
.venv/bin/python -m pytest tests/test_mcp_collaboration_handler.py tests/test_mcp.py
.venv/bin/p2p validate
.venv/bin/python -m pytest
```
