# P2PWorkspace Work Review Suggestion Helper Extraction Tasks

## Phase 1: Audit

- [x] T001 Identify Work review suggestion helpers in `storage.filesystem`.
- [x] T002 Confirm runtime usage is only through `WorkBranchService`.
- [x] T003 Confirm focused tests can keep an override callback.

## Phase 2: Extraction

- [x] T004 Move Work review suggestion URL helpers into `services.work_branches`.
- [x] T005 Make `WorkBranchService` use the service-owned helper by default.
- [x] T006 Remove review suggestion callback injection from `P2PWorkspace`.
- [x] T007 Remove Work review suggestion helpers from `storage.filesystem`.
- [x] T008 Confirm `storage.filesystem` retains only YAML/path/slug/facade-local helpers.

## Phase 3: Verification

- [x] T009 Run focused Work branch service tests.
- [x] T010 Run focused CLI/MCP Work review regressions.
- [x] T011 Run `p2p validate`.
- [x] T012 Run the full pytest suite.
- [x] T013 Update the refactoring status tracker.
