# P2PWorkspace Work Retire Service Ownership Tasks

## Phase 1: Audit

- [x] T001 Confirm Work planning metadata behavior already lives in
      `WorkPlanningService`.
- [x] T002 Confirm `P2PWorkspace.retire_work()` is the remaining Work planning
      lifecycle behavior in the facade.
- [x] T003 Confirm CLI uses the public workspace facade and does not need a
      command contract change.

## Phase 2: Service Move

- [x] T004 Add `WorkRetire` to `services.work_planning`.
- [x] T005 Implement `WorkPlanningService.retire()`.
- [x] T006 Change `P2PWorkspace.retire_work()` to delegate to the service.
- [x] T007 Remove the duplicate `WorkRetire` dataclass from
      `storage.filesystem` if no longer needed.

## Phase 3: Verification

- [x] T008 Add focused service test coverage for Work retirement.
- [x] T009 Run focused Work planning and CLI Work retirement tests.
- [x] T010 Run `p2p validate`.
- [x] T011 Run the full pytest suite.
- [x] T012 Update the refactoring status tracker.
