# P2PWorkspace Governance Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `filesystem.py` after project initialization extraction.

- [x] T002: Select governance/vote as a bounded remaining runtime cluster with
  clear facade methods and CLI consumers.

- [x] T003: Map consumers: collaboration CLI, direct workspace calls, and
  choice lifecycle tests that record votes.

- [x] T004: Define out-of-scope boundaries: no governance semantics changes, no
  proposal decision service changes, no CLI formatting changes, no MCP changes,
  no branch/sync behavior.

## Phase 2 - Focused Tests First

- [x] T005: Add direct service test for governance initialization writing
  expected files and status counts.

- [x] T006: Add direct service test for invalid governance mode validation.

- [x] T007: Add direct service test for vote recording, counts, winner, and
  persisted `result` data.

- [x] T008: Add direct service test for tied vote status.

- [x] T009: Add direct service test for malformed `votes.yml` validation.

- [x] T010: Add direct service test for decision precedent sequencing and
  proposal existence validation.

## Phase 3 - Service Extraction

- [x] T011: Create `src/p2p_engine/services/governance.py` with status
  dataclasses, YAML helpers, and vote status calculation.

- [x] T012: Move governance bootstrap file assembly into `GovernanceService`.

- [x] T013: Move governance status loading/counting into `GovernanceService`.

- [x] T014: Move vote recording/status behavior into `GovernanceService`.

- [x] T015: Move decision precedent recording into `GovernanceService`.

- [x] T016: Add lazy `P2PWorkspace` governance service factory.

- [x] T017: Delegate existing `P2PWorkspace` governance/vote/precedent methods
  to the service.

- [x] T018: Remove now-unused `_vote_status_from_data()` from
  `storage/filesystem.py`.

## Phase 4 - Compatibility Verification

- [x] T019: Run focused governance service tests.

- [x] T020: Run focused collaboration CLI tests.

- [x] T021: Run choice lifecycle tests that record votes.

- [x] T022: Run `.venv/bin/p2p validate`.

- [x] T023: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T024: Review source scope with `git status --short`.

- [x] T025: Confirm no CLI/MCP formatting, branch/sync, proposal decision, or
  governance semantics changed.

- [x] T026: Update `requirements.md` statuses after verification.

- [x] T027: Record implementation evidence in `design.md`.

- [x] T028: Update the global refactoring tracker.

- [x] T029: Mark all tasks complete only after evidence exists.

## Current Status

Completed.
