# MCP Collaboration Handler Domain Split Tasks

## Tasks

### Phase 1 - Baseline

- [x] T001: Inspect the current collaboration handler responsibilities and line
  count; completion is recorded in `design.md`.
- [x] T002: Run focused collaboration handler tests before extraction.

### Phase 2 - Remote And Consent Module

- [x] T003: Create `src/p2p_engine/mcp/handlers/collaboration_remote.py`.
- [x] T004: Move remote profile, permissions, consent request/status/show
  handling into `handle_collaboration_remote_tool()`.
- [x] T005: Preserve return payloads and governance fields.

### Phase 3 - Sync Module

- [x] T006: Create `src/p2p_engine/mcp/handlers/collaboration_sync.py`.
- [x] T007: Move sync status/fetch/pull/push handling into
  `handle_collaboration_sync_tool()`.
- [x] T008: Preserve consent validation, head tracking, error marking, audit
  commit, and push behavior.

### Phase 4 - Proposal Branch Module

- [x] T009: Create `src/p2p_engine/mcp/handlers/collaboration_proposals.py`.
- [x] T010: Move proposal draft commit, branch, branch status, publish,
  request-review, accept/reject branch, merge, finalize, and cleanup handling
  into `handle_collaboration_proposal_tool()`.
- [x] T011: Preserve merge conflict consent error payloads and governance
  response fields.

### Phase 5 - Public Router

- [x] T012: Reduce `collaboration.py` to the public router that calls remote,
  sync, and proposal collaboration handlers.
- [x] T013: Verify unrelated tools still return `None`.
- [x] T014: Verify `mcp.tools.call_tool()` still routes collaboration tools
  through the public handler.

### Phase 6 - Tracker And Verification

- [x] T015: Update
  `specs/features/p2pworkspace-modular-refactoring-contract/refactoring-status.md`
  with the completed step and line-count summary.
- [x] T016: Run focused collaboration/MCP tests.
- [x] T017: Run `.venv/bin/p2p validate`.
- [x] T018: Run the full test suite.
- [x] T019: Mark tasks complete only after evidence exists.

## Current Binding Status

All tasks are complete. Focused collaboration/MCP tests, `.venv/bin/p2p
validate`, and the full test suite passed after the split.
