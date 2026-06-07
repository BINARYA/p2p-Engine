# P2PWorkspace Governance Result Type Cleanup Tasks

## Phase 1: Audit

- [x] T001 Identify duplicated result types in `storage.filesystem`.
- [x] T002 Confirm owning services define and construct equivalent dataclasses.
- [x] T003 Exclude facade-owned models that need separate analysis.
- [x] T004 Identify unused consent receipt conversion helper.

## Phase 2: Cleanup

- [x] T005 Import proposal result types from `services.proposals`.
- [x] T006 Import readiness result types from `services.readiness`.
- [x] T007 Import permission actor result type from `services.permissions`.
- [x] T008 Import consent receipt result type from `services.consent`.
- [x] T009 Remove duplicate dataclasses from `storage.filesystem`.
- [x] T010 Remove unused `_consent_receipt_from_payload()`.
- [x] T011 Confirm duplicate definitions and unused helper no longer remain.

## Phase 3: Verification

- [x] T012 Run focused service tests for proposals, readiness, permissions, and
      consent.
- [x] T013 Run focused CLI/MCP regression tests for affected commands.
- [x] T014 Run `p2p validate`.
- [x] T015 Run the full pytest suite.
- [x] T016 Update the refactoring status tracker.
