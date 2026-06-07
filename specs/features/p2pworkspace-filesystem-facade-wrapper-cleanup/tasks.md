# P2PWorkspace Filesystem Facade Wrapper Cleanup Tasks

## Phase 1: Audit

- [x] T001 List remaining private wrappers in `storage.filesystem`.
- [x] T002 Identify wrappers still used as service callbacks or by focused tests.
- [x] T003 Identify no-caller wrappers with equivalent service ownership.

## Phase 2: Cleanup

- [x] T004 Remove no-caller consent compatibility wrappers.
- [x] T005 Remove no-caller project assessment and spec export wrappers.
- [x] T006 Remove no-caller Work planning summary/id wrappers.
- [x] T007 Remove no-caller registry/proposal branch/sync wrappers.
- [x] T008 Confirm preserved wrappers are still intentional composition points.

## Phase 3: Verification

- [x] T009 Run focused service tests for affected service ownership areas.
- [x] T010 Run focused CLI/MCP regressions for affected command surfaces.
- [x] T011 Run `p2p validate`.
- [x] T012 Run the full pytest suite.
- [x] T013 Update the refactoring status tracker.
