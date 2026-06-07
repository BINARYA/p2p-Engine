# P2PWorkspace Dead Filesystem Helper Cleanup Tasks

## Phase 1: Audit

- [x] T001 List low-level helpers still present in `storage.filesystem`.
- [x] T002 Identify helpers with active callers.
- [x] T003 Identify helpers with no callers and equivalent service ownership.

## Phase 2: Cleanup

- [x] T004 Remove unused permission/consent constants and normalizers.
- [x] T005 Remove unused legacy permission payload builder.
- [x] T006 Remove unused legacy proposal markdown and exploration renderers.
- [x] T007 Remove unused legacy status/conflict helpers.
- [x] T008 Remove unused support helpers made dead by the cleanup.
- [x] T009 Confirm only active helpers remain in `storage.filesystem`.

## Phase 3: Verification

- [x] T010 Run focused proposal/permission/consent/branch tests.
- [x] T011 Run focused CLI/MCP regression tests for affected areas.
- [x] T012 Run `p2p validate`.
- [x] T013 Run the full pytest suite.
- [x] T014 Update the refactoring status tracker.
