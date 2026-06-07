# P2PWorkspace Proposal Branch Lifecycle Service Extraction Design

## Current Behavior

Managed proposal branch behavior is currently concentrated in
`storage/filesystem.py`. It mixes proposal document lookup, Git branch
operations, remote collision detection, metadata writes, lifecycle transitions,
merge conflict handling, cleanup, and scan registry generation.

## Target Boundary

Create `src/p2p_engine/services/proposal_branches.py`.

The service owns:

- proposal branch result dataclasses;
- branch metadata read/write helpers;
- branch name and hash generation;
- branch status rendering from metadata;
- proposal branch scan registry generation;
- lifecycle transition orchestration for branch, publish, review, retire,
  accept, reject, merge, continue, abort, finalize, and cleanup.

The service does not own:

- CLI output;
- MCP schemas, dispatch, consent checks, or consent receipt lifecycle;
- raw Git subprocess calls;
- remote profile persistence;
- proposal document CRUD;
- Work branch lifecycle.

## Extraction Strategy

This feature is intentionally split into smaller phases because the lifecycle is
high-risk.

1. Read-only foundation:
   - result dataclasses;
   - metadata read helpers;
   - `show_proposal_branch`;
   - `scan_proposal_branches`.
2. Branch creation:
   - branch name/hash generation;
   - clean worktree and base branch guards;
   - branch metadata commit.
3. Publish and request review:
   - remote selection;
   - remote collision detection;
   - auto-renumber;
   - provider advisory metadata.
4. Branch decision:
   - retire;
   - accept;
   - reject.
5. Merge:
   - merge;
   - merge conflict metadata;
   - continue;
   - abort.
6. Finalize and cleanup:
   - base branch push;
   - local/remote branch deletion;
   - cleanup metadata push.

Each phase must preserve `P2PWorkspace` as the compatibility facade.

## Compatibility Tests

Mapped CLI tests include:

```bash
.venv/bin/pytest \
  tests/test_cli.py::test_cli_proposal_branch_creates_managed_branch_metadata \
  tests/test_cli.py::test_cli_proposal_publish_request_review_and_scan \
  tests/test_cli.py::test_cli_proposal_publish_auto_renumbers_on_remote_id_collision \
  tests/test_cli.py::test_cli_proposal_publish_detects_collision_from_remote_main \
  tests/test_cli.py::test_cli_proposal_retire_branch_records_reason \
  tests/test_cli.py::test_cli_proposal_merge_merges_reviewed_branch_into_base \
  tests/test_cli.py::test_cli_proposal_accept_branch_records_governance_decision \
  tests/test_cli.py::test_cli_proposal_finalize_pushes_merged_base_branch \
  tests/test_cli.py::test_cli_proposal_cleanup_deletes_local_and_remote_branch
```

Mapped MCP tests include:

```bash
.venv/bin/pytest \
  tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools \
  tests/test_mcp.py::test_mcp_proposal_branch_refuses_proposal_branch_base_without_opt_in \
  tests/test_mcp.py::test_mcp_requested_consent_does_not_authorize_publish \
  tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent
```

The final feature completion check is:

```bash
.venv/bin/pytest
.venv/bin/p2p validate
```
