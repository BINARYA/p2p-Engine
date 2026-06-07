# P2PWorkspace Work Branch Lifecycle Service Extraction Design

## Current Behavior

Managed Work branch behavior is still concentrated in `storage/filesystem.py`.
It mixes Work manifest reads/writes, Git branch operations, review/publish
metadata, merge conflict handling, finalize/cleanup, and scan registry
generation.

## Target Boundary

Create `src/p2p_engine/services/work_branches.py`.

The service owns:

- Work branch result dataclasses;
- Work branch scan registry generation;
- branch, submit, review, publish, external review request;
- accept, merge conflict, continue, abort;
- finalize and cleanup.

The service does not own:

- Work plan creation and summary rendering;
- CLI output;
- MCP schemas, dispatch, consent checks, or consent receipt lifecycle;
- raw Git subprocess calls;
- remote profile persistence.

## Extraction Strategy

This feature is split into phases to keep the refactor reviewable:

1. Read-only foundation:
   - result dataclasses;
   - `scan_work_branches`.
2. Branch and submit:
   - `branch_work`;
   - `submit_work`.
3. Local review and publish:
   - `review_work`;
   - `publish_work`.
4. External review request:
   - provider advisory metadata.
5. Accept and conflict handling:
   - `accept_work`;
   - `continue_accept_work`;
   - `abort_accept_work`.
6. Finalize and cleanup:
   - `finalize_work`;
   - `cleanup_work`.

Each phase keeps `P2PWorkspace` as the compatibility facade.

## Compatibility Tests

Mapped CLI tests include:

```bash
.venv/bin/pytest \
  tests/test_cli.py::test_cli_work_branch_creates_managed_branch \
  tests/test_cli.py::test_cli_work_branch_requires_clean_worktree \
  tests/test_cli.py::test_cli_work_review_requests_local_review \
  tests/test_cli.py::test_cli_work_review_requires_submitted_clean_branch \
  tests/test_cli.py::test_cli_work_publish_pushes_reviewed_branch \
  tests/test_cli.py::test_cli_work_publish_requires_review_and_remote \
  tests/test_cli.py::test_cli_work_request_review_records_provider_handoff \
  tests/test_cli.py::test_cli_work_accept_merges_published_branch \
  tests/test_cli.py::test_cli_work_accept_requires_published_base_branch \
  tests/test_cli.py::test_cli_work_finalize_requires_accepted_and_remote \
  tests/test_cli.py::test_cli_work_cleanup_requires_finalized_branch \
  tests/test_cli.py::test_cli_work_scan_reads_local_branch_without_checkout
```

The final feature completion check is:

```bash
.venv/bin/pytest
.venv/bin/p2p validate
```
