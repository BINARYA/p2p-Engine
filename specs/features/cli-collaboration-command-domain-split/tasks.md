# CLI Collaboration Command Domain Split Tasks

## Tasks

### Phase 1 - Baseline

- [x] T001: Inspect current `collaboration.py` command groups and line count;
  completion is recorded in `design.md`.
- [x] T002: Run focused CLI tests before extraction.

### Phase 2 - Governance Commands

- [x] T003: Create `src/p2p_engine/cli_commands/governance.py`.
- [x] T004: Move governance, vote, and precedent command registration into
  `register_governance_commands(governance_app, vote_app, precedent_app)`.
- [x] T005: Preserve governance command output and error handling.

### Phase 3 - Analysis Commands

- [x] T006: Create `src/p2p_engine/cli_commands/project_analysis.py`.
- [x] T007: Move impact and conflict command registration into
  `register_project_analysis_commands(impact_app, conflict_app)`.
- [x] T008: Preserve impact/conflict command output and error handling.

### Phase 4 - Registry Commands

- [x] T009: Create `src/p2p_engine/cli_commands/registry.py`.
- [x] T010: Move registry refresh/status/show command registration into
  `register_registry_commands(registry_app)`.
- [x] T011: Preserve registry rendering behavior.

### Phase 5 - Intake Commands

- [x] T012: Create `src/p2p_engine/cli_commands/intake.py`.
- [x] T013: Move intake and intake apply command registration into
  `register_intake_commands(intake_app, intake_apply_app)`.
- [x] T014: Preserve intake command output and error handling.

### Phase 6 - Choice Commands

- [x] T015: Create `src/p2p_engine/cli_commands/choices.py`.
- [x] T016: Move choice command registration into
  `register_choice_commands(choice_app)`.
- [x] T017: Preserve choice command output, validation, and blocker behavior.

### Phase 7 - Public Wrapper

- [x] T018: Reduce `collaboration.py` to the public wrapper imported by `cli.py`.
- [x] T019: Verify `cli.py` does not need import or registration changes.
- [x] T020: Verify command registration still exposes all collaboration-related
  command groups through the CLI app.

### Phase 8 - Tracker And Verification

- [x] T021: Update
  `specs/features/p2pworkspace-modular-refactoring-contract/refactoring-status.md`
  with completed step and line-count summary.
- [x] T022: Run focused CLI tests.
- [x] T023: Run `.venv/bin/p2p validate`.
- [x] T024: Run the full test suite.
- [x] T025: Mark tasks complete only after evidence exists.

## Current Binding Status

All tasks are complete. Focused CLI tests, `.venv/bin/p2p validate`, and the
full test suite passed after the split.
