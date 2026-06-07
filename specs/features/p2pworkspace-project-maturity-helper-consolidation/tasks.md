# P2PWorkspace Project Maturity Helper Consolidation Tasks

## Phase 1: Audit

- [x] T001 Identify `project_maturity` local YAML helper behavior.
- [x] T002 Confirm non-mapping YAML error text differs from foundation default.
- [x] T003 Choose custom error support instead of changing service behavior.

## Phase 2: Consolidation

- [x] T004 Extend `foundation.files.read_yaml_mapping` with optional custom error message.
- [x] T005 Add focused foundation tests for custom error message behavior.
- [x] T006 Replace `project_maturity` YAML dump helper with foundation import.
- [x] T007 Replace `project_maturity` YAML mapping helper with foundation-backed wrapper.
- [x] T008 Remove unused imports from `project_maturity`.
- [x] T009 Confirm no local YAML serialization/parsing implementation remains in `project_maturity`.

## Phase 3: Verification

- [x] T010 Run focused project maturity and foundation tests.
- [x] T011 Run focused CLI/MCP project assessment/maturity regressions.
- [x] T012 Run `p2p validate`.
- [x] T013 Run the full pytest suite.
- [x] T014 Update the refactoring status tracker.
