# P2PWorkspace Context Packet Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `filesystem.py` after proposal prompt/artifact extraction.

- [x] T002: Select context packet assembly as the next bounded extraction
  because it is read-only, facade-oriented, and consumed by CLI/MCP.

- [x] T003: Map consumers: project status CLI context command, MCP project
  context handler, and direct workspace calls.

- [x] T004: Define out-of-scope boundaries: no context content policy changes,
  no next-action generation changes, no registry refresh changes, no CLI/MCP
  formatting changes.

## Phase 2 - Focused Tests First

- [x] T005: Add direct service test for small default packet state,
  do-not-read guidance, allowed commands, and bounded next step.

- [x] T006: Add direct service test for medium proposal target including
  problem/proposal summaries and target-specific commands.

- [x] T007: Add direct service test for change, choice, and work target artifact
  shapes.

- [x] T008: Add direct service test for invalid budget validation.

- [x] T009: Add direct service test for invalid target prefix validation.

## Phase 3 - Service Extraction

- [x] T010: Create `src/p2p_engine/services/context_packets.py` with
  `ContextPacket`, `ContextPacketService`, and local helper functions.

- [x] T011: Move current-state assembly into the service.

- [x] T012: Move default artifact selection into the service.

- [x] T013: Move targeted artifact selection into the service.

- [x] T014: Move allowed command and bounded next-step calculation into the
  service.

- [x] T015: Add lazy `P2PWorkspace` context packet service factory.

- [x] T016: Delegate `P2PWorkspace.context_packet()` to the service.

- [x] T017: Remove now-unused context helper methods and `ContextPacket`
  dataclass from `storage/filesystem.py`.

## Phase 4 - Compatibility Verification

- [x] T018: Run focused context packet service tests.

- [x] T019: Run focused CLI context tests.

- [x] T020: Run focused MCP context tests.

- [x] T021: Run `.venv/bin/p2p validate`.

- [x] T022: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T023: Review source scope with `git status --short`.

- [x] T024: Confirm no CLI/MCP formatting, next-action generation, registry
  refresh, Git/sync, or content policy behavior changed.

- [x] T025: Update `requirements.md` statuses after verification.

- [x] T026: Record implementation evidence in `design.md`.

- [x] T027: Update the global refactoring tracker.

- [x] T028: Mark all tasks complete only after evidence exists.

## Current Status

Completed.
