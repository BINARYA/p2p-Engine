# P2PWorkspace Registry Record Builder Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `filesystem.py` after project context renderer extraction.

- [x] T002: Select registry record builder extraction as the next focused slice
  because record construction remains a large runtime cluster in the facade.

- [x] T003: Map consumers: `RegistryService`, `ProjectStateService`,
  `NextActionService`, `ChoiceLifecycleService`, conflict memory, validation,
  CLI registry commands, and MCP registry tools.

- [x] T004: Define out-of-scope boundaries: no registry file schema changes, no
  registry write semantics changes, no readiness computation changes, no
  lifecycle behavior changes.

## Phase 2 - Focused Tests First

- [x] T005: Add direct record builder test for accepted proposals and proposal
  registry records.

- [x] T006: Add direct record builder test for decision and readiness records.

- [x] T007: Add direct record builder test for change records and
  `_changes_for_proposal()` relation lookup.

- [x] T008: Add direct record builder test for choice records from choice
  directories and proposal votes.

- [x] T009: Add direct record builder test for relation and artifact records.

## Phase 3 - Service Extraction

- [x] T010: Create `src/p2p_engine/services/registry_records.py` with
  `RegistryRecordBuilderService` and local read/cleanup helpers.

- [x] T011: Move accepted proposal record construction into the service.

- [x] T012: Move proposal, decision, change, choice, relation, artifact, and
  readiness record builders into the service.

- [x] T013: Add lazy `P2PWorkspace` registry record builder service factory.

- [x] T014: Delegate existing `P2PWorkspace` registry helper methods to the
  record builder service.

- [x] T015: Keep `RegistryService` wiring compatible by passing the same facade
  helper methods.

- [x] T016: Remove now-unused registry record implementation code from
  `storage/filesystem.py`.

## Phase 4 - Compatibility Verification

- [x] T017: Run focused registry record builder service tests.

- [x] T018: Run registry service tests.

- [x] T019: Run next actions and choice lifecycle tests that consume registry
  record callbacks.

- [x] T020: Run `.venv/bin/p2p validate`.

- [x] T021: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T022: Review source scope with `git status --short`.

- [x] T023: Confirm no registry schema/write, readiness computation, lifecycle,
  CLI/MCP formatting, Git/sync, or prompt behavior changed.

- [x] T024: Update `requirements.md` statuses after verification.

- [x] T025: Record implementation evidence in `design.md`.

- [x] T026: Update the global refactoring tracker.

- [x] T027: Mark all tasks complete only after evidence exists.

## Current Status

Completed.
