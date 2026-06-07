# CLI Proposal Command Domain Split Tasks

## Tasks

### Phase 1 - Baseline

- [x] T001: Inspect current `proposals.py` command groups and line count;
  completion is recorded in `design.md`.
- [x] T002: Run focused CLI tests before extraction.

### Phase 2 - Proposal Core

- [x] T003: Create `src/p2p_engine/cli_commands/proposal_core.py`.
- [x] T004: Move proposal create/update/list/show commands into
  `register_proposal_core_commands(proposal_app)`.
- [x] T005: Preserve proposal core command output and error handling.

### Phase 3 - Readiness

- [x] T006: Create `src/p2p_engine/cli_commands/proposal_readiness.py`.
- [x] T007: Move readiness show/refresh/init/explain commands and readiness
  rendering into `register_proposal_readiness_commands(proposal_readiness_app)`.
- [x] T008: Preserve readiness warning and explanation output.

### Phase 4 - Branch Lifecycle

- [x] T009: Create `src/p2p_engine/cli_commands/proposal_branches.py`.
- [x] T010: Move branch/status/publish/request-review/merge/accept-branch/
  reject-branch/finalize/cleanup/retire-branch/scan commands into
  `register_proposal_branch_commands(proposal_app)`.
- [x] T011: Preserve merge conflict exit behavior and branch rendering output.

### Phase 5 - Decisions

- [x] T012: Create `src/p2p_engine/cli_commands/proposal_decisions.py`.
- [x] T013: Move proposal accept/reject/defer and `decision record` commands into
  `register_proposal_decision_commands(proposal_app, decision_app)`.
- [x] T014: Preserve readiness override behavior for proposal acceptance.

### Phase 6 - Contributions

- [x] T015: Create `src/p2p_engine/cli_commands/proposal_contributions.py`.
- [x] T016: Move legacy and nested contribution add/list commands into
  `register_proposal_contribution_commands(...)`.
- [x] T017: Preserve contribution output and aliases.

### Phase 7 - Public Wrapper

- [x] T018: Reduce `proposals.py` to the public wrapper imported by `cli.py`.
- [x] T019: Verify `cli.py` does not need import or registration changes.
- [x] T020: Verify command registration still exposes all proposal-related
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
