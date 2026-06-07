# P2PWorkspace Conflict Memory Service Extraction Tasks

## Phase 1 - Baseline And Scope

- [x] T001 Record current conflict public methods and storage behavior in
  `storage/filesystem.py`.
- [x] T002 Record current CLI and MCP conflict consumers.
- [x] T003 Run focused baseline tests for conflict behavior before code
  movement.

## Phase 2 - Service Skeleton

- [x] T004 Add `src/p2p_engine/services/conflicts.py`.
- [x] T005 Move or recreate the `ConflictStatus` dataclass in the service
  module.
- [x] T006 Import and re-export `ConflictStatus` from
  `p2p_engine.storage.filesystem` for compatibility.
- [x] T007 Add `ConflictMemoryService` constructor with `root`, `p2p_dir`, and
  `find_proposal_dir` dependency.
- [x] T008 Add a cached `_conflict_memory_service()` factory to `P2PWorkspace`.

## Phase 3 - Runtime Extraction

- [x] T009 Move conflict path resolution into the service.
- [x] T010 Move conflict payload read behavior into the service.
- [x] T011 Implement service `status(...)` and delegate
  `P2PWorkspace.conflict_status(...)`.
- [x] T012 Implement service `record(...)` and delegate
  `P2PWorkspace.record_conflict(...)`.
- [x] T013 Remove obsolete inline conflict implementation from
  `storage/filesystem.py`.
- [x] T014 Confirm CLI and MCP modules do not import `ConflictMemoryService`
  directly.

## Phase 4 - Tests

- [x] T015 Add direct service tests for empty status.
- [x] T016 Add direct service tests for record lifecycle and winner handling.
- [x] T017 Add direct service tests for invalid proposal count and invalid
  winner.
- [x] T018 Add direct service tests for invalid `conflicts.yml` shape.
- [x] T019 Run focused CLI conflict tests.
- [x] T020 Run focused MCP conflict tests.
- [x] T021 Run full test suite.
- [x] T022 Run `.venv/bin/p2p validate`.
- [x] T023 Update the central refactoring status tracker.

## Current Progress

- Runtime extraction completed locally.
- Focused service, CLI, and MCP conflict tests pass.
- Full suite passes with 303 tests.
- `.venv/bin/p2p validate` passes with 0 findings.
