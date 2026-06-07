# P2PWorkspace Foundation Helper Service Consolidation 2 Tasks

## Phase 1: Audit

- [x] T001 Compare selected service helper behavior with `foundation.files`.
- [x] T002 Identify tolerant YAML mapping readers that must not use the strict helper.
- [x] T003 Select low-risk services with focused tests.

## Phase 2: Consolidation

- [x] T004 Add tolerant `read_yaml_mapping_or_default` to `foundation.files`.
- [x] T005 Add focused foundation tests for tolerant YAML mapping reads.
- [x] T006 Replace helper definitions in `services.remote_profile`.
- [x] T007 Replace helper definitions in `services.permissions`.
- [x] T008 Replace helper definitions in `services.consent`.
- [x] T009 Replace YAML dump helper in `services.project_state`.
- [x] T010 Remove unused imports from changed services.
- [x] T011 Confirm no selected-service duplicate helper definitions remain.

## Phase 3: Verification

- [x] T012 Run focused tests for changed services and foundation helpers.
- [x] T013 Run focused CLI/MCP regressions for remote, permissions, consent, and project state.
- [x] T014 Run `p2p validate`.
- [x] T015 Run the full pytest suite.
- [x] T016 Update the refactoring status tracker.
