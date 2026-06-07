# P2PWorkspace Workspace Status Service Extraction Tasks

## Phase 1: Audit

- [x] T001 Identify status/check/proposal summary behavior still implemented in
      `P2PWorkspace`.
- [x] T002 Confirm remaining facade dataclasses owned by that behavior.
- [x] T003 Exclude `ProposalDraftCommit` because it belongs to Git-backed draft
      commit behavior.

## Phase 2: Service Extraction

- [x] T004 Add `services.workspace_status` with result dataclasses and helpers.
- [x] T005 Implement `WorkspaceStatusService.status()`.
- [x] T006 Implement `WorkspaceStatusService.proposal_summaries()`.
- [x] T007 Implement `WorkspaceStatusService.check()`.
- [x] T008 Add lazy service wiring in `P2PWorkspace`.
- [x] T009 Delegate public facade methods to the service.
- [x] T010 Remove moved dataclasses and unused helper functions from
      `storage.filesystem`.

## Phase 3: Verification

- [x] T011 Add focused service and facade tests.
- [x] T012 Run focused workspace status/check/proposal summary CLI/MCP tests.
- [x] T013 Run `p2p validate`.
- [x] T014 Run the full pytest suite.
- [x] T015 Update the refactoring status tracker.
