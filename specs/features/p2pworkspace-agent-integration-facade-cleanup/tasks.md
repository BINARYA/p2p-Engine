# P2PWorkspace Agent Integration Facade Cleanup Tasks

## Phase 1: Audit

- [x] T001 Identify private agent integration facade wrappers.
- [x] T002 Confirm active references to those wrappers.
- [x] T003 Select the minimal rewiring needed for validation.

## Phase 2: Cleanup

- [x] T004 Wire `ValidationService` to `AgentInstructionService.path`.
- [x] T005 Remove unused private agent integration wrapper methods from
      `P2PWorkspace`.
- [x] T006 Confirm no stale wrapper references remain.

## Phase 3: Verification

- [x] T007 Run focused agent instruction and validation tests.
- [x] T008 Run focused CLI/MCP agent integration regression tests.
- [x] T009 Run `p2p validate`.
- [x] T010 Run the full pytest suite.
- [x] T011 Update the refactoring status tracker.
