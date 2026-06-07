# P2PWorkspace Foundation Helper Service Consolidation 5 Tasks

## Phase 1: Audit

- [x] T001 Compare `changes` YAML/slug helper behavior with foundation contracts.
- [x] T002 Compare `intake` YAML helper behavior with foundation contracts.
- [x] T003 Confirm `project_maturity` remains excluded due to distinct error text.

## Phase 2: Consolidation

- [x] T004 Replace helper definitions in `services.changes`.
- [x] T005 Replace helper definitions in `services.intake`.
- [x] T006 Remove unused imports from changed services.
- [x] T007 Confirm no selected-service duplicate helper definitions remain.

## Phase 3: Verification

- [x] T008 Run focused tests for changed services.
- [x] T009 Run focused CLI/MCP regressions for Change Set and Intake surfaces.
- [x] T010 Run `p2p validate`.
- [x] T011 Run the full pytest suite.
- [x] T012 Update the refactoring status tracker.
