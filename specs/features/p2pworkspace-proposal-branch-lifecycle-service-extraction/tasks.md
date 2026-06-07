# P2PWorkspace Proposal Branch Lifecycle Service Extraction Tasks

## Phase 1 - Analysis And Specification

- [x] T001: Confirm roadmap position after sync extraction.
- [x] T002: Inspect current proposal branch lifecycle methods in
  `storage/filesystem.py`.
- [x] T003: Inspect mapped CLI proposal branch lifecycle tests.
- [x] T004: Inspect mapped MCP proposal branch lifecycle and consent-gated
  tests.
- [x] T005: Create local requirements, design, and implementation task files.
- [x] T006: Add global refactoring tracker so remaining work is visible.

## Phase 2 - Read-Only Foundation

- [x] T007: Create `src/p2p_engine/services/proposal_branches.py` with
  proposal branch result dataclasses and read-only helpers.
- [x] T008: Add focused service tests for unbranched status, metadata-backed
  status, malformed scan input tolerance, and scan registry output.
- [x] T009: Delegate `P2PWorkspace.show_proposal_branch` to the service.
- [x] T010: Delegate `P2PWorkspace.scan_proposal_branches` to the service.
- [x] T011: Keep proposal document lookup and Git ref reads injected through
  callbacks.
- [x] T012: Run focused read-only proposal branch service tests.
- [x] T013: Run mapped CLI status/scan compatibility tests.
- [x] T014: Run mapped MCP status/scan compatibility tests.

## Phase 3 - Branch Creation

- [x] T015: Move branch name/hash generation into the service.
- [x] T016: Move `branch_proposal` clean worktree, base branch, and existing
  branch guards into the service.
- [x] T017: Delegate `P2PWorkspace.branch_proposal` to the service.
- [x] T018: Add focused tests for detached HEAD, dirty worktree, proposal base
  refusal, explicit base checkout, and branch metadata shape.
- [x] T019: Run mapped CLI and MCP branch creation tests.

## Phase 4 - Publish And Request Review

- [x] T020: Move publish guard behavior and remote selection into the service.
- [x] T021: Move remote proposal ID collision detection into the service.
- [x] T022: Move auto-renumber behavior into the service.
- [x] T023: Move request-review provider advisory metadata into the service.
- [x] T024: Delegate `publish_proposal_branch` and
  `request_proposal_branch_review` to the service.
- [x] T025: Add focused tests for publish guards, remote missing, collision,
  auto-renumber metadata, and provider validation.
- [x] T026: Run mapped CLI/MCP publish and request-review tests.

## Phase 5 - Branch Decision

- [x] T027: Move retire behavior into the service.
- [x] T028: Move accept/reject branch decision behavior into the service.
- [x] T029: Delegate retire, accept, reject, and internal decision helper to
  the service.
- [x] T030: Add focused tests for reason requirements, allowed statuses, and
  decision metadata.
- [x] T031: Run mapped CLI/MCP decision tests.

## Phase 6 - Merge And Conflict Handling

- [x] T032: Move merge guard behavior into the service.
- [x] T033: Move merge conflict metadata behavior into the service.
- [x] T034: Move merge continue behavior into the service.
- [x] T035: Move merge abort behavior into the service.
- [x] T036: Delegate merge, continue, and abort methods to the service.
- [x] T037: Add focused tests for merge status guards, wrong base branch, dirty
  worktree, conflict metadata, continue unresolved conflicts, and abort.
- [x] T038: Run mapped CLI/MCP merge tests.

## Phase 7 - Finalize And Cleanup

- [x] T039: Move finalize behavior into the service.
- [x] T040: Move cleanup behavior into the service.
- [x] T041: Delegate finalize and cleanup methods to the service.
- [x] T042: Add focused tests for finalize status/remote guards and cleanup
  local/remote deletion metadata.
- [x] T043: Run mapped CLI/MCP finalize and cleanup tests.

## Phase 8 - Full Verification

- [x] T044: Run Python compile checks for touched runtime modules.
- [x] T045: Run full test suite.
- [x] T046: Run `.venv/bin/p2p validate`.
- [x] T047: Confirm no Work branch lifecycle behavior moved into proposal
  branch service.
- [x] T048: Confirm no CLI/MCP presentation or consent receipt lifecycle moved
  into proposal branch service.
- [x] T049: Record completion evidence in this task file.

## Current Progress Evidence

Phase 2 read-only foundation completed.

- Focused service tests: `.venv/bin/pytest tests/test_proposal_branch_service.py`
  -> `4 passed`.
- Mapped CLI/MCP status and scan tests:
  `.venv/bin/pytest tests/test_cli.py::test_cli_proposal_branch_creates_managed_branch_metadata tests/test_cli.py::test_cli_proposal_publish_request_review_and_scan tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools`
  -> `3 passed`.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/proposal_branches.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite after Phase 2: `.venv/bin/pytest` -> `206 passed`.
- P2P validation after Phase 2: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check: the service currently owns only result dataclasses, metadata
  read, `show`, and `scan`; publish, review, branch decision, merge, finalize,
  cleanup, consent handling, CLI, and MCP remain outside this extracted slice.

Phase 3 branch creation completed.

- Focused service tests: `.venv/bin/pytest tests/test_proposal_branch_service.py`
  -> `8 passed`.
- Mapped CLI/MCP branch creation tests:
  `.venv/bin/pytest tests/test_cli.py::test_cli_proposal_branch_creates_managed_branch_metadata tests/test_mcp.py::test_mcp_safe_managed_sync_and_proposal_branch_tools tests/test_mcp.py::test_mcp_proposal_branch_refuses_proposal_branch_base_without_opt_in`
  -> `3 passed`.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/proposal_branches.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite after Phase 3: `.venv/bin/pytest` -> `210 passed`.
- P2P validation after Phase 3: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check: branch name/hash generation and `branch_proposal` guard
  behavior now live in `services.proposal_branches`; publish, review,
  branch decision, merge, finalize, cleanup, consent handling, CLI, and MCP
  remain outside this extracted slice.

Phase 4 publish and request-review completed.

- Focused service tests: `.venv/bin/pytest tests/test_proposal_branch_service.py`
  -> `13 passed`.
- Mapped CLI/MCP publish and request-review tests:
  `.venv/bin/pytest tests/test_cli.py::test_cli_proposal_publish_request_review_and_scan tests/test_cli.py::test_cli_proposal_publish_auto_renumbers_on_remote_id_collision tests/test_cli.py::test_cli_proposal_publish_detects_collision_from_remote_main tests/test_mcp.py::test_mcp_requested_consent_does_not_authorize_publish tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent`
  -> `5 passed`.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/proposal_branches.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite after Phase 4: `.venv/bin/pytest` -> `215 passed`.
- P2P validation after Phase 4: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check: publish guards, remote selection, remote collision detection,
  auto-renumber, push orchestration, and request-review provider advisory
  metadata now live in `services.proposal_branches`; branch decisions, merge,
  finalize, cleanup, consent handling, CLI, and MCP remain outside this
  extracted slice.

Phase 5 branch decision completed.

- Focused service tests: `.venv/bin/pytest tests/test_proposal_branch_service.py`
  -> `19 passed`.
- Mapped CLI/MCP decision tests:
  `.venv/bin/pytest tests/test_cli.py::test_cli_proposal_retire_branch_records_reason tests/test_cli.py::test_cli_proposal_accept_branch_records_governance_decision tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent`
  -> `3 passed`.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/proposal_branches.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite after Phase 5: `.venv/bin/pytest` -> `221 passed`.
- P2P validation after Phase 5: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check: retire, accept, reject, and branch decision metadata now live
  in `services.proposal_branches`; merge, finalize, cleanup, consent handling,
  CLI, and MCP remain outside this extracted slice.

Phase 6 merge and conflict handling completed.

- Focused service tests: `.venv/bin/pytest tests/test_proposal_branch_service.py`
  -> `24 passed`.
- Mapped CLI/MCP merge tests:
  `.venv/bin/pytest tests/test_cli.py::test_cli_proposal_merge_merges_reviewed_branch_into_base tests/test_cli.py::test_cli_proposal_accept_branch_records_governance_decision tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent`
  -> `3 passed`.
- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/proposal_branches.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite after Phase 6: `.venv/bin/pytest` -> `226 passed`.
- P2P validation after Phase 6: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check: merge guards, merge conflict metadata, merge continue, and
  merge abort now live in `services.proposal_branches`; finalize, cleanup,
  consent handling, CLI, and MCP remain outside this extracted slice.

Phase 7 finalize and cleanup completed.

- Focused service tests: `.venv/bin/pytest tests/test_proposal_branch_service.py`
  -> `28 passed`.
- Mapped CLI/MCP finalize and cleanup tests:
  `.venv/bin/pytest tests/test_cli.py::test_cli_proposal_finalize_pushes_merged_base_branch tests/test_cli.py::test_cli_proposal_cleanup_deletes_local_and_remote_branch tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent`
  -> `4 passed`.
- Boundary check: finalize and cleanup now live in
  `services.proposal_branches`; consent handling, CLI, and MCP remain outside
  the service.

Feature completion verification.

- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/services/proposal_branches.py src/p2p_engine/storage/filesystem.py`
  -> passed.
- Full suite after Phase 7: `.venv/bin/pytest` -> `230 passed`.
- P2P validation after Phase 7: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check: no Work branch lifecycle behavior was moved into
  `services.proposal_branches`; CLI presentation, MCP schemas/dispatch, and
  consent receipt lifecycle remain outside the service.
