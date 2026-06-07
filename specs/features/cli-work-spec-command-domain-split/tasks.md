# CLI Work/Spec Command Domain Split Tasks

## Tasks

### Phase 1 - Baseline

- [x] T001: Inspect current `work_specs.py` command groups and line count;
  completion is recorded in `design.md`.
- [x] T002: Run focused CLI tests before extraction.

### Phase 2 - Change Commands

- [x] T003: Create `src/p2p_engine/cli_commands/changes.py`.
- [x] T004: Move `p2p change` command registration into
  `register_change_commands(change_app)`.
- [x] T005: Preserve all Change Set command output and error handling.

### Phase 3 - Spec Commands

- [x] T006: Create `src/p2p_engine/cli_commands/specs.py`.
- [x] T007: Move `p2p spec` command registration into
  `register_spec_commands(spec_app)`.
- [x] T008: Preserve all software spec command output and error handling.

### Phase 4 - Work Commands

- [x] T009: Create `src/p2p_engine/cli_commands/work.py`.
- [x] T010: Move `p2p work` command registration into
  `register_work_commands(work_app)`.
- [x] T011: Preserve `WorkAcceptConflict` handling, exit code behavior, and
  Work command output.

### Phase 5 - Public Wrapper

- [x] T012: Reduce `work_specs.py` to the public wrapper imported by `cli.py`.
- [x] T013: Verify `cli.py` does not need import or registration changes.
- [x] T014: Verify command registration still exposes `change`, `spec`, and
  `work` command groups through the CLI app.

### Phase 6 - Tracker And Verification

- [x] T015: Update
  `specs/features/p2pworkspace-modular-refactoring-contract/refactoring-status.md`
  with completed step and line-count summary.
- [x] T016: Run focused CLI tests.
- [x] T017: Run `.venv/bin/p2p validate`.
- [x] T018: Run the full test suite.
- [x] T019: Mark tasks complete only after evidence exists.

## Current Binding Status

All tasks are complete. Focused CLI tests, `.venv/bin/p2p validate`, and the
full test suite passed after the split.
