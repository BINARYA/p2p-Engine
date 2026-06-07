# CLI Command Module Split Tasks

## Phase 1 - Shared CLI Foundation

- [x] T001 Create local requirements and design for CLI module split.
- [x] T002 Extract shared CLI helpers out of `src/p2p_engine/cli.py`.
- [x] T003 Keep `src/p2p_engine/cli.py` as the public Typer app compatibility surface.
- [x] T004 Run focused CLI tests covering init, doctor, next actions, and agent integration.

## Phase 2 - Low-Risk Command Groups

- [x] T005 Extract doctor and runtime diagnostics commands.
- [x] T006 Extract agent integration commands.
- [x] T007 Extract next-action commands.
- [x] T008 Extract project/status/context/validation/assessment commands.

## Phase 3 - Domain Command Groups

- [x] T009 Extract proposal document/readiness/contribution/decision commands.
- [x] T010 Extract prompt workflow commands.
- [x] T011 Extract project, remote, sync, permissions, and consent commands.
- [x] T012 Extract change/spec/export/work commands.
- [x] T013 Extract intake, choice, governance, vote, precedent, conflict, and impact commands.

## Phase 4 - Final Verification

- [x] T014 Verify command registration and help output remain compatible.
- [x] T015 Run focused CLI command tests after each group extraction.
- [x] T016 Run full test suite.
- [x] T017 Run `p2p validate`.
- [x] T018 Update `refactoring-status.md`.
