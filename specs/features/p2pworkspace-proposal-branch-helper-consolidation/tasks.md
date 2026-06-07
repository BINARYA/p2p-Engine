# P2PWorkspace Proposal Branch Helper Consolidation Tasks

## Phase 1: Audit

- [x] T001 Identify local file YAML helpers in `services.proposal_branches`.
- [x] T002 Identify raw Git-ref YAML parsing that must remain local.
- [x] T003 Confirm slug fallback behavior can be preserved with `fallback=""`.

## Phase 2: Consolidation

- [x] T004 Replace local YAML dump helper with foundation import.
- [x] T005 Replace local tolerant YAML mapping helper with foundation import.
- [x] T006 Replace local slug helper with foundation-backed wrapper.
- [x] T007 Confirm direct `yaml.safe_load` remains only for Git-ref text parsing.
- [x] T008 Confirm no local file YAML helper definitions remain.

## Phase 3: Verification

- [x] T009 Run focused proposal branch and foundation tests.
- [x] T010 Run focused CLI/MCP proposal branch lifecycle regressions.
- [x] T011 Run `p2p validate`.
- [x] T012 Run the full pytest suite.
- [x] T013 Update the refactoring status tracker.
