# P2PWorkspace Work Branch Lifecycle Service Extraction Tasks

## Phase 1 - Analysis And Specification

- [x] T001: Confirm roadmap position after proposal branch lifecycle extraction.
- [x] T002: Inspect current Work branch lifecycle methods in
  `storage/filesystem.py`.
- [x] T003: Inspect mapped CLI/MCP Work branch lifecycle tests.
- [x] T004: Create local requirements, design, and implementation task files.
- [x] T005: Update global refactoring tracker so Work branch lifecycle is
  visible as the active extraction.

## Phase 2 - Read-Only Foundation

- [x] T006: Create `src/p2p_engine/services/work_branches.py` with Work branch
  result dataclasses and read-only helpers.
- [x] T007: Add focused service tests for Work branch scan registry output,
  malformed YAML tolerance, ignored non-manifest files, and branch metadata
  extraction.
- [x] T008: Delegate `P2PWorkspace.scan_work_branches` to the service.
- [x] T009: Keep Git ref reads injected through callbacks.
- [x] T010: Run focused read-only Work branch service tests.
- [x] T011: Run mapped CLI Work branch scan compatibility tests.

## Phase 3 - Branch And Submit

- [x] T012: Move `branch_work` manifest validation, Git guards, branch
  creation, and manifest update behavior into the service.
- [x] T013: Move `submit_work` changed-file guard, manifest update, and commit
  behavior into the service.
- [x] T014: Delegate `branch_work` and `submit_work` to the service.
- [x] T015: Add focused tests for planned-only branch, dirty worktree, wrong
  base branch, manifest git shape, submit without changes, and submit
  manifest-only changes.
- [x] T016: Run mapped CLI branch/submit compatibility tests.

## Phase 4 - Review And Publish

- [x] T017: Move local review behavior into the service.
- [x] T018: Move publish behavior into the service.
- [x] T019: Delegate `review_work` and `publish_work`.
- [x] T020: Add focused tests for submitted-only review, clean branch guard,
  review metadata, review-required publish, remote missing, and push metadata.
- [x] T021: Run mapped CLI/MCP review/publish compatibility tests.

## Phase 5 - External Review Request

- [x] T022: Move external review provider advisory metadata into the service.
- [x] T023: Delegate `request_external_work_review`.
- [x] T024: Add focused tests for provider fallback, local provider conversion,
  invalid provider, remote URL fallback, and suggested next text.
- [x] T025: Run mapped CLI/MCP external review compatibility tests.

## Phase 6 - Accept And Conflict Handling

- [x] T026: Move `accept_work` guard behavior and branch manifest read behavior
  into the service.
- [x] T027: Move accept merge conflict metadata into the service.
- [x] T028: Move `continue_accept_work` behavior into the service.
- [x] T029: Move `abort_accept_work` behavior into the service.
- [x] T030: Delegate accept, continue, and abort methods.
- [x] T031: Add focused tests for accepted merge, unpublished branch manifest,
  conflict metadata, unresolved conflict markers, continue, and abort.
- [x] T032: Run mapped CLI/MCP accept compatibility tests.

## Phase 7 - Finalize And Cleanup

- [x] T033: Move `finalize_work` behavior into the service.
- [x] T034: Move `cleanup_work` behavior into the service.
- [x] T035: Delegate finalize and cleanup methods.
- [x] T036: Add focused tests for accepted-only finalize, remote missing,
  finalized-only cleanup, local/remote deletion, and cleanup metadata.
- [x] T037: Run mapped CLI/MCP finalize and cleanup compatibility tests.

## Phase 8 - Full Verification

- [x] T038: Run Python compile checks for touched runtime modules.
- [x] T039: Run full test suite.
- [x] T040: Run `.venv/bin/p2p validate`.
- [x] T041: Confirm no proposal branch lifecycle behavior moved into Work
  branch service.
- [x] T042: Confirm no CLI/MCP presentation or consent receipt lifecycle moved
  into Work branch service.
- [x] T043: Record completion evidence in this task file.

## Current Progress Evidence

Phase 2 read-only foundation completed.

- Focused service tests: `.venv/bin/pytest tests/test_work_branch_service.py`
  -> `4 passed`.
- Mapped CLI scan test:
  `.venv/bin/pytest tests/test_cli.py::test_cli_work_scan_reads_local_branch_without_checkout`
  -> `1 passed`.
- Boundary check: `services.work_branches` currently owns Work result
  dataclasses and `scan` only; branch, submit, review, publish, accept,
  finalize, cleanup, consent handling, CLI, and MCP remain outside this
  extracted slice.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite after Phase 2: `.venv/bin/pytest` -> `234 passed`.
- P2P validation after Phase 2: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.

Phase 3 branch/submit extraction implemented.

- Runtime change: `P2PWorkspace.branch_work` delegates to
  `WorkBranchService.branch`; `P2PWorkspace.submit_work` delegates to
  `WorkBranchService.submit`.
- Focused test coverage added in `tests/test_work_branch_service.py` for:
  planned-only branch guard, dirty worktree guard, wrong base branch guard,
  invalid manifest `git` shape, branch manifest metadata updates, submit
  metadata updates, submit without changes, and submit manifest-only changes.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py tests/test_work_branch_service.py`
  -> passed.
- Focused service tests:
  `.venv/bin/python -m pytest tests/test_work_branch_service.py`
  -> `12 passed`.
- Mapped CLI branch/submit compatibility tests:
  `.venv/bin/python -m pytest tests/test_cli.py::test_cli_work_branch_creates_managed_branch tests/test_cli.py::test_cli_work_branch_requires_clean_worktree tests/test_cli.py::test_cli_work_submit_creates_local_commit tests/test_cli.py::test_cli_work_submit_requires_non_manifest_changes`
  -> `4 passed`.
- P2P validation after environment restore: `.venv/bin/p2p validate` ->
  `errors: 0`, `warnings: 0`, `infos: 0`.
- Compile check after environment restore:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py tests/test_work_branch_service.py`
  -> passed.
- Full suite after Phase 3: `.venv/bin/python -m pytest` -> `242 passed`.

Phase 4 review/publish extraction implemented.

- Runtime change: `P2PWorkspace.review_work` delegates to
  `WorkBranchService.review`; `P2PWorkspace.publish_work` delegates to
  `WorkBranchService.publish`.
- Focused test coverage added in `tests/test_work_branch_service.py` for:
  submitted-only review guard, dirty worktree review guard, review metadata
  update, review metadata commit, review-required publish guard, missing remote
  guard, required review metadata shape, publish metadata update, publish
  metadata commit, and branch push callback.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py tests/test_work_branch_service.py`
  -> passed.
- Focused service tests:
  `.venv/bin/python -m pytest tests/test_work_branch_service.py`
  -> `19 passed`.
- Mapped CLI review/publish compatibility tests:
  `.venv/bin/python -m pytest tests/test_cli.py::test_cli_work_review_requests_local_review tests/test_cli.py::test_cli_work_review_requires_submitted_clean_branch tests/test_cli.py::test_cli_work_publish_pushes_reviewed_branch tests/test_cli.py::test_cli_work_publish_requires_review_and_remote`
  -> `4 passed`.
- Full suite after Phase 4: `.venv/bin/python -m pytest` -> `249 passed`.
- P2P validation after Phase 4: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.

Phase 5 external review request extraction implemented.

- Runtime change: `P2PWorkspace.request_external_work_review` delegates to
  `WorkBranchService.request_external_review`.
- Focused test coverage added in `tests/test_work_branch_service.py` for:
  profile provider fallback, explicit invalid provider rejection,
  `local` provider conversion to `generic`, publish metadata URL use, Git
  remote URL fallback, missing remote URL guard, dirty worktree guard,
  metadata commit, and `suggested_next` propagation.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py tests/test_work_branch_service.py`
  -> passed.
- Focused service tests:
  `.venv/bin/python -m pytest tests/test_work_branch_service.py`
  -> `25 passed`.
- Mapped CLI external review compatibility test:
  `.venv/bin/python -m pytest tests/test_cli.py::test_cli_work_request_review_records_provider_handoff`
  -> `1 passed`.
- Full suite after Phase 5: `.venv/bin/python -m pytest` -> `255 passed`.
- P2P validation after Phase 5: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.

Phase 6 accept and conflict handling extraction implemented.

- Runtime change: `P2PWorkspace.accept_work`,
  `P2PWorkspace.continue_accept_work`, and
  `P2PWorkspace.abort_accept_work` delegate to `WorkBranchService`.
- Focused test coverage added in `tests/test_work_branch_service.py` for:
  accepted merge metadata, unpublished branch manifest guard, merge conflict
  metadata, unresolved conflict marker guard, successful continue after
  resolution, abort merge metadata restore, and abort detail callback.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py tests/test_work_branch_service.py`
  -> passed.
- Focused service tests:
  `.venv/bin/python -m pytest tests/test_work_branch_service.py`
  -> `31 passed`.
- Mapped CLI accept compatibility tests:
  `.venv/bin/python -m pytest tests/test_cli.py::test_cli_work_accept_merges_published_branch tests/test_cli.py::test_cli_work_accept_requires_published_base_branch tests/test_cli.py::test_cli_work_accept_conflict_continue_and_abort`
  -> `3 passed`.
- Full suite after Phase 6: `.venv/bin/python -m pytest` -> `261 passed`.
- P2P validation after Phase 6: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.

Phase 7 finalize and cleanup extraction implemented.

- Runtime change: `P2PWorkspace.finalize_work` and
  `P2PWorkspace.cleanup_work` delegate to `WorkBranchService`.
- Focused test coverage added in `tests/test_work_branch_service.py` for:
  accepted-only finalize guard, missing finalize remote guard, finalize
  metadata and base-branch push, finalized-only cleanup guard, missing managed
  branch guard, local branch deletion, optional remote branch deletion, cleanup
  metadata, cleanup commit, and cleanup metadata push.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py tests/test_work_branch_service.py`
  -> passed.
- Focused service tests:
  `.venv/bin/python -m pytest tests/test_work_branch_service.py`
  -> `37 passed`.
- Mapped CLI finalize/cleanup compatibility tests:
  `.venv/bin/python -m pytest tests/test_cli.py::test_cli_work_accept_merges_published_branch tests/test_cli.py::test_cli_work_finalize_requires_accepted_and_remote tests/test_cli.py::test_cli_work_cleanup_requires_finalized_branch`
  -> `3 passed`.

Phase 8 full verification completed.

- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/work_branches.py src/p2p_engine/storage/filesystem.py tests/test_work_branch_service.py`
  -> passed.
- Full suite after Phase 7: `.venv/bin/python -m pytest` -> `267 passed`.
- P2P validation after Phase 7: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check:
  `rg -n "Proposal|proposal_|p2p proposal|typer|mcp|consent|Consent|click|Option|Argument" src/p2p_engine/services/work_branches.py`
  -> no matches. Proposal branch lifecycle, CLI/MCP presentation, and consent
  receipt lifecycle were not moved into the Work branch service.
