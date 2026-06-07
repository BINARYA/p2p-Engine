# MCP Consent Audit Helper Extraction Tasks

## Phase 1 - Analysis And Specification

- [x] T001: Confirm roadmap position after Work branch lifecycle completion.
- [x] T002: Inspect current consent-audit helpers in `mcp/tools.py`.
- [x] T003: Inspect mapped MCP consent-gated tests.
- [x] T004: Create local requirements, design, and implementation task files.

## Phase 2 - Helper Module Extraction

- [x] T005: Create `src/p2p_engine/mcp/consent_audit.py`.
- [x] T006: Move safe Git HEAD read helper into the new module.
- [x] T007: Move sync consent target resolution into the new module.
- [x] T008: Move consume-with-audit and commit/push audit helpers into the new
  module.
- [x] T009: Move used-with-error-on-HEAD-change helper into the new module.
- [x] T010: Update `mcp/tools.py` imports/call sites and remove duplicate helper
  implementations.

## Phase 3 - Focused Tests

- [x] T011: Add focused tests for sync consent target success and detached HEAD
  guard.
- [x] T012: Add focused tests for consume-with-audit commit and optional push.
- [x] T013: Add focused tests for audit commit failure and audit push failure.
- [x] T014: Add focused tests for used-with-error marking only when HEAD
  changes.

## Phase 4 - Compatibility Verification

- [x] T015: Run mapped MCP consent-gated sync tests.
- [x] T016: Run mapped MCP proposal publish/request-review tests.
- [x] T017: Run mapped MCP proposal decision and branch lifecycle tests.
- [x] T018: Run focused helper tests.

## Phase 5 - Full Verification

- [x] T019: Run Python compile checks for touched MCP modules and tests.
- [x] T020: Run full test suite.
- [x] T021: Run `.venv/bin/p2p validate`.
- [x] T022: Confirm MCP schemas and dispatch tool names remain in `mcp/tools.py`.
- [x] T023: Confirm no proposal/sync/domain lifecycle behavior moved into the
  consent audit helper.
- [x] T024: Record completion evidence in this task file.

## Current Progress Evidence

Feature initialized after `p2pworkspace-work-branch-lifecycle-service-extraction`
was marked done in the local refactoring tracker.

Phase 2 helper module extraction completed.

- Added `src/p2p_engine/mcp/consent_audit.py`.
- `mcp/tools.py` imports the helper functions and no longer defines local
  duplicates for safe head reads, sync consent target resolution,
  consume-with-audit, audit commit/push, or used-with-error-on-HEAD-change.

Phase 3 focused helper tests added.

- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/mcp/consent_audit.py src/p2p_engine/mcp/tools.py tests/test_mcp_consent_audit.py`
  -> passed.
- Focused helper tests:
  `.venv/bin/python -m pytest tests/test_mcp_consent_audit.py`
  -> `6 passed`.

Phase 4 mapped MCP compatibility tests completed.

- Mapped consent-gated MCP tests:
  `.venv/bin/python -m pytest tests/test_mcp.py::test_mcp_sync_push_requires_and_consumes_consent tests/test_mcp.py::test_mcp_sync_pull_requires_and_consumes_consent tests/test_mcp.py::test_mcp_proposal_publish_requires_and_consumes_consent tests/test_mcp.py::test_mcp_proposal_request_review_requires_and_consumes_consent tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent tests/test_mcp.py::test_mcp_proposal_merge_requires_and_consumes_consent tests/test_mcp.py::test_mcp_proposal_finalize_requires_and_consumes_consent tests/test_mcp.py::test_mcp_proposal_reject_and_cleanup_require_consent`
  -> `9 passed`.

Phase 5 full verification completed.

- Compile check:
  `.venv/bin/python -m compileall src/p2p_engine/mcp/consent_audit.py src/p2p_engine/mcp/tools.py tests/test_mcp_consent_audit.py`
  -> passed.
- Full suite: `.venv/bin/python -m pytest` -> `273 passed`.
- P2P validation: `.venv/bin/p2p validate` -> `errors: 0`,
  `warnings: 0`, `infos: 0`.
- Boundary check:
  `rg -n "TOOL_NAMES|inputSchema|if name ==|def call_tool|def list_tools" src/p2p_engine/mcp/tools.py src/p2p_engine/mcp/consent_audit.py`
  -> matches only in `mcp/tools.py`; tool names, schemas, and dispatch remain
  in the MCP transport module.
