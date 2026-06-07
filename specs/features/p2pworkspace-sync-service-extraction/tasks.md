# P2PWorkspace Sync Service Extraction Tasks

## Phase 1 - Analysis And Specification

- [x] T001: Confirm roadmap position after project assessment extraction.
- [x] T002: Inspect current `P2PWorkspace` sync methods and helper methods.
- [x] T003: Inspect mapped CLI sync tests and MCP consent-gated sync tests.
- [x] T004: Create local requirements, design, and implementation task files
  for the sync extraction.

## Phase 2 - Focused Service Coverage

- [x] T005: Add focused sync service tests for non-repository, local profile
  with Git origin, explicit remote override, URL mismatch, and missing remote
  diagnostics.
- [x] T006: Add focused sync service tests for fetch/pull/push adapter
  delegation and failure messages.
- [x] T007: Add focused sync service tests for detached HEAD and dirty
  worktree guards.

## Phase 3 - Service Extraction

- [x] T008: Create `src/p2p_engine/services/sync.py` with `SyncStatus`,
  `SyncResult`, and `SyncService`.
- [x] T009: Move selected remote resolution and sync status computation into
  `SyncService` without changing reason strings.
- [x] T010: Move fetch/pull/push orchestration and guard behavior into
  `SyncService` without changing error messages.
- [x] T011: Keep Git operations injected through adapter callables; do not add
  raw subprocess behavior to the service.

## Phase 4 - Facade Delegation

- [x] T012: Add lazy `P2PWorkspace._sync_service()` factory.
- [x] T013: Delegate `P2PWorkspace.sync_status`, `sync_fetch`, `sync_pull`,
  `sync_push`, `_sync_remote`, and `_require_sync_remote` to the service.
- [x] T014: Remove duplicated sync implementation from `P2PWorkspace` after
  facade delegation is verified.

## Phase 5 - Compatibility Verification

- [x] T015: Run focused sync service tests.
- [x] T016: Run mapped CLI sync compatibility tests.
- [x] T017: Run mapped MCP sync and consent-gated compatibility tests.
- [x] T018: Run Python compile check for touched runtime modules.
- [x] T019: Run full test suite.
- [x] T020: Run `.venv/bin/p2p validate`.

## Phase 6 - Completion Review

- [x] T021: Confirm no proposal branch lifecycle or Work branch lifecycle
  behavior moved into the sync service.
- [x] T022: Confirm no CLI/MCP presentation behavior moved into the service.
- [x] T023: Record completion evidence in this task file.

## Completion Evidence

- Focused service tests: `.venv/bin/pytest tests/test_sync_service.py` ->
  `9 passed`.
- Mapped CLI sync tests:
  `.venv/bin/pytest tests/test_cli.py::test_cli_sync_status_reports_local_project_without_remote tests/test_cli.py::test_cli_sync_status_detects_git_origin_when_p2p_profile_is_local tests/test_cli.py::test_cli_sync_status_detects_remote_profile_url_mismatch tests/test_cli.py::test_cli_sync_push_fetch_and_pull_wrap_git_remote tests/test_cli.py::test_cli_sync_pull_requires_clean_worktree`
  -> `5 passed`.
- Mapped MCP sync/consent tests:
  `.venv/bin/pytest tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent`
  -> `3 passed`.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/sync.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite: `.venv/bin/pytest` -> `202 passed`.
- P2P validation: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check: `src/p2p_engine/services/sync.py` contains no CLI, MCP,
  consent, proposal branch lifecycle, or Work branch lifecycle behavior.
