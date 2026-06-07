# P2PWorkspace Foundation Helper Service Consolidation 4 Tasks

## Phase 1: Audit

- [x] T001 Compare `proposals` YAML/slug helper behavior with foundation contracts.
- [x] T002 Compare `readiness` YAML helper behavior with foundation contracts.
- [x] T003 Compare `choices` YAML/slug helper behavior with foundation contracts.
- [x] T004 Exclude `changes`, `intake`, and `project_maturity` for later focused tranches.

## Phase 2: Consolidation

- [x] T005 Extend `foundation.files.slugify` with a fallback parameter.
- [x] T006 Add focused foundation tests for slug fallback behavior.
- [x] T007 Replace helper definitions in `services.proposals`.
- [x] T008 Replace helper definitions in `services.readiness`.
- [x] T009 Replace helper definitions in `services.choices`.
- [x] T010 Remove unused imports from changed services.
- [x] T011 Confirm no selected-service duplicate helper definitions remain.

## Phase 3: Verification

- [x] T012 Run focused tests for changed services.
- [x] T013 Run focused CLI/MCP regressions for proposal, readiness, and choice surfaces.
- [x] T014 Run `p2p validate`.
- [x] T015 Run the full pytest suite.
- [x] T016 Update the refactoring status tracker.
