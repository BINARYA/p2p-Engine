# P2PWorkspace Foundation Helper Service Consolidation 1 Tasks

## Phase 1: Audit

- [x] T001 List services with duplicated YAML/path/slug helpers.
- [x] T002 Select low-risk services with dedicated tests.
- [x] T003 Confirm selected helper behavior matches `foundation.files`.

## Phase 2: Consolidation

- [x] T004 Replace helper definitions in `services.conflicts`.
- [x] T005 Replace helper definitions in `services.project_assessment`.
- [x] T006 Replace helper definitions in `services.next_actions`.
- [x] T007 Remove unused imports from changed services.
- [x] T008 Confirm no local duplicate helper definitions remain in selected services.

## Phase 3: Verification

- [x] T009 Run focused tests for changed services and foundation helpers.
- [x] T010 Run focused CLI/MCP regressions for project status/actions/conflicts.
- [x] T011 Run `p2p validate`.
- [x] T012 Run the full pytest suite.
- [x] T013 Update the refactoring status tracker.
