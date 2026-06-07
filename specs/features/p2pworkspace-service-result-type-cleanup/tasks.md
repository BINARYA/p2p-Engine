# P2PWorkspace Service Result Type Cleanup Tasks

## Phase 1: Audit

- [x] T001 Identify duplicated service-owned result dataclasses in
      `storage.filesystem`.
- [x] T002 Confirm owning services define and construct equivalent result
      dataclasses.
- [x] T003 Exclude models whose ownership is not yet cleanly service-owned.

## Phase 2: Cleanup

- [x] T004 Import project state result types from `services.project_state`.
- [x] T005 Import project assessment result type from
      `services.project_assessment`.
- [x] T006 Import registry result types from `services.registries`.
- [x] T007 Import software spec result types from `services.software_spec`.
- [x] T008 Import spec export result types from `services.spec_export`.
- [x] T009 Import remote profile result type from `services.remote_profile`.
- [x] T010 Remove duplicate result dataclasses from `storage.filesystem`.
- [x] T011 Confirm duplicate definitions no longer remain in
      `storage.filesystem`.

## Phase 3: Verification

- [x] T012 Run focused tests for affected services.
- [x] T013 Run focused CLI/MCP regression tests for affected commands.
- [x] T014 Run `p2p validate`.
- [x] T015 Run the full pytest suite.
- [x] T016 Update the refactoring status tracker.
