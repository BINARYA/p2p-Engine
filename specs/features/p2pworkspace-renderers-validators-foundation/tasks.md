# P2PWorkspace Renderers Validators Foundation Tasks

## Phase 1 - Preparation

- [x] T001: Review current shared Markdown/YAML helper use in
  `src/p2p_engine/storage/filesystem.py`; completion is a list of helpers to
  move and domain renderers to leave in place.

- [x] T002: Capture compatibility test commands from the feature design;
  completion is a ready-to-run command list.

## Phase 2 - Focused Tests First

- [x] T003: Add focused Markdown helper tests for title reading, section
  reading, pending suppression, section existence, section replacement,
  frontmatter read/replace, invalid frontmatter fallback, and title stripping.

- [x] T004: Add focused YAML validator tests for tasks YAML, top-level key
  validation, and invalid YAML error paths.

## Phase 3 - Foundation Extraction

- [x] T005: Create `src/p2p_engine/foundation/markdown.py`; completion is a
  pure helper module with no workspace, CLI, MCP, or Git imports.

- [x] T006: Move shared Markdown helpers behind the foundation module while
  preserving behavior.

- [x] T007: Create `src/p2p_engine/foundation/validators.py`; completion is a
  pure validator module with no workspace, CLI, MCP, or Git imports.

- [x] T008: Move generic YAML validators behind the foundation module while
  preserving error message fragments.

- [x] T009: Update `src/p2p_engine/storage/filesystem.py` to import and use the
  foundation helpers under existing private names.

- [x] T010: Confirm domain renderers and domain validators remain in place for
  later service-specific extractions.

## Phase 4 - Compatibility Verification

- [x] T011: Run focused foundation tests; completion is reviewed passing output.

- [x] T012: Run mapped compatibility tests; completion is reviewed passing
  output.

- [x] T013: Run `.venv/bin/p2p validate`; completion is reviewed output with no
  errors.

- [x] T014: Run the full test suite; completion is reviewed passing output.

## Phase 5 - Traceability And Completion

- [x] T015: Review `git diff` for source scope; completion confirms changes are
  limited to foundation modules, imports/delegation, focused tests, and local
  feature specs.

- [x] T016: Update this feature's `requirements.md` statuses only after tests
  and validation pass.

- [x] T017: Record implementation evidence in `design.md`; completion lists
  helpers moved, helpers left in place, tests run, and remaining gaps.

- [x] T018: Mark tasks complete only with evidence; completion is all checked
  tasks backed by source diff, test output, validation output, or design notes.

## Current Status

Runtime extraction is complete for this feature. Focused foundation tests,
mapped compatibility tests, full test suite, and `.venv/bin/p2p validate` pass.
