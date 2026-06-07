# P2PWorkspace Work Planning Result Type Cleanup Tasks

## Phase 1: Audit

- [x] T001 Confirm `WorkPlanningService` owns `WorkStatus`, `WorkDetail`, and
      `WorkSummary`.
- [x] T002 Confirm duplicate dataclasses in `storage.filesystem` are used only
      for facade annotations.
- [x] T003 Confirm public facade methods can keep the same names while
      returning service-owned types.

## Phase 2: Cleanup

- [x] T004 Import Work planning result types from `services.work_planning`.
- [x] T005 Remove duplicate `WorkStatus`, `WorkDetail`, and `WorkSummary`
      dataclasses from `storage.filesystem`.
- [x] T006 Confirm no duplicate class definitions remain in `storage.filesystem`.

## Phase 3: Verification

- [x] T007 Run focused Work planning tests.
- [x] T008 Run focused CLI/MCP/context tests that consume Work planning results.
- [x] T009 Run `p2p validate`.
- [x] T010 Run the full pytest suite.
- [x] T011 Update the refactoring status tracker.
