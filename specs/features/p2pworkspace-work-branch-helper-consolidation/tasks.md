# P2PWorkspace Work Branch Helper Consolidation Tasks

## Phase 1: Audit

- [x] T001 Identify local file YAML helpers in `services.work_branches`.
- [x] T002 Identify raw Git-ref YAML parsing that must remain local.
- [x] T003 Confirm conflict marker and review suggestion helpers remain service-local.

## Phase 2: Consolidation

- [x] T004 Replace local YAML dump helper with foundation import.
- [x] T005 Replace local tolerant YAML mapping helper with foundation import.
- [x] T006 Confirm direct `yaml.safe_load` remains only for Git-ref text parsing.
- [x] T007 Confirm no local file YAML helper definitions remain.

## Phase 3: Verification

- [x] T008 Run focused Work branch and foundation tests.
- [x] T009 Run focused CLI/MCP Work branch lifecycle regressions.
- [x] T010 Run `p2p validate`.
- [x] T011 Run the full pytest suite.
- [x] T012 Update the refactoring status tracker.
