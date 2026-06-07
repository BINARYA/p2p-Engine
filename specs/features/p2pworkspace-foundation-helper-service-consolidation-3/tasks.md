# P2PWorkspace Foundation Helper Service Consolidation 3 Tasks

## Phase 1: Audit

- [x] T001 Compare `software_spec` helper behavior with foundation contracts.
- [x] T002 Compare `registries` helper behavior with foundation contracts.
- [x] T003 Compare `agent_instructions` helper behavior with foundation contracts.
- [x] T004 Exclude `project_maturity` because its YAML error message differs.

## Phase 2: Consolidation

- [x] T005 Replace helper definitions in `services.software_spec`.
- [x] T006 Replace helper definitions in `services.registries`.
- [x] T007 Replace helper definitions in `services.agent_instructions`.
- [x] T008 Remove unused imports from changed services.
- [x] T009 Confirm no selected-service duplicate helper definitions remain.

## Phase 3: Verification

- [x] T010 Run focused tests for changed services.
- [x] T011 Run focused CLI/MCP regressions for software spec, registries, and agent instructions.
- [x] T012 Run `p2p validate`.
- [x] T013 Run the full pytest suite.
- [x] T014 Update the refactoring status tracker.
