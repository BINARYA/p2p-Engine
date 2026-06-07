# P2PWorkspace Remote Profile Service Extraction Tasks

## Phase 1 - Preparation

- [x] T001: Run full baseline tests before runtime changes; completion is
  reviewed passing output.

- [x] T002: Review current remote profile implementation in
  `src/p2p_engine/storage/filesystem.py`; completion is a note identifying
  exact methods/helpers to move and sync helpers to leave behind.

- [x] T003: Capture current compatibility test list from this feature design;
  completion is a test command block ready to run after extraction.

## Phase 2 - Focused Tests First

- [x] T004: Add focused remote profile service tests for local and remote
  default payload generation.

- [x] T005: Add focused remote profile service tests for profile read fallback,
  configure local, configure remote with explicit URL, and configure remote
  with Git URL fallback.

- [x] T006: Add focused negative-path tests for invalid initialization and
  configure inputs.

## Phase 3 - Service Extraction

- [x] T007: Create `src/p2p_engine/services/remote_profile.py`; completion is a
  service with no Typer, Rich, MCP, branch lifecycle, or sync imports.

- [x] T008: Move remote profile payload generation behind the service while
  preserving local/cloud project initialization behavior.

- [x] T009: Move remote profile read and configure behavior behind the service
  while preserving `.p2p/project.yml` storage shape.

- [x] T010: Delegate `P2PWorkspace.remote_profile` and
  `P2PWorkspace.configure_remote_profile` to the service.

- [x] T011: Update project initialization to obtain the same remote payload
  through the service boundary.

- [x] T012: Confirm sync methods and branch methods still consume the facade
  and were not folded into the remote profile service.

## Phase 4 - Compatibility Verification

- [x] T013: Run focused remote profile service tests; completion is reviewed
  passing output.

- [x] T014: Run mapped CLI remote/sync compatibility tests; completion is
  reviewed passing output.

- [x] T015: Run mapped MCP remote compatibility tests; completion is reviewed
  passing output.

- [x] T016: Run `.venv/bin/p2p validate`; completion is reviewed output with no
  errors.

## Phase 5 - Traceability And Completion

- [x] T017: Review `git diff` for source scope; completion confirms changes are
  limited to the service, facade delegation, focused tests, and local feature
  specs.

- [x] T018: Update this feature's `requirements.md` statuses only after tests
  and validation pass.

- [x] T019: Record implementation evidence in `design.md`; completion lists
  facade methods delegated, helpers moved, helpers left in place, tests run,
  and remaining gaps.

- [x] T020: Mark tasks complete only with evidence; completion is all checked
  tasks backed by source diff, test output, validation output, or design notes.

## Current Status

Runtime extraction is complete for this feature. Focused service tests, mapped
CLI/MCP compatibility tests, full test suite, and `.venv/bin/p2p validate`
pass.
