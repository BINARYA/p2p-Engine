# P2PWorkspace Foundation File Helper Extraction Tasks

## Phase 1: Audit

- [x] T001 Identify generic module-level helpers in `storage.filesystem`.
- [x] T002 Classify facade-specific helpers that should remain local.
- [x] T003 Confirm scope excludes broad service-wide YAML helper consolidation.

## Phase 2: Extraction

- [x] T004 Add `p2p_engine.foundation.files` with slug/path/YAML helpers.
- [x] T005 Add focused foundation tests for the extracted helper contracts.
- [x] T006 Update `storage.filesystem` to import and use foundation helpers.
- [x] T007 Remove duplicated generic helper definitions and unused imports from `storage.filesystem`.
- [x] T008 Confirm `storage.filesystem` keeps only facade-local helper messages.

## Phase 3: Verification

- [x] T009 Run focused foundation and filesystem-related service tests.
- [x] T010 Run focused CLI/MCP validation and Work/spec regressions.
- [x] T011 Run `p2p validate`.
- [x] T012 Run the full pytest suite.
- [x] T013 Update the refactoring status tracker.
