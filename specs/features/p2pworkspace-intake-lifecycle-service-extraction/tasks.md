# P2PWorkspace Intake Lifecycle Service Extraction Tasks

## Phase 1 - Baseline And Scope

- [x] T001 Record current intake public methods and private helpers in
  `storage/filesystem.py`.
- [x] T002 Record current CLI, MCP, next-action, and context consumers.
- [x] T003 Run focused baseline tests for intake behavior before code movement.

## Phase 2 - Service Skeleton

- [x] T004 Add `src/p2p_engine/services/intake.py`.
- [x] T005 Move or recreate `IntakePrompt`, `IntakeStatus`,
  `IntakeApplyPlan`, and `IntakeAppliedAction` in the service module.
- [x] T006 Import and re-export intake dataclasses from
  `p2p_engine.storage.filesystem` for compatibility.
- [x] T007 Add `IntakeLifecycleService` constructor with `root`, `p2p_dir`,
  `registry_status`, `intake_context`, `add_contribution`, and
  `create_choice` dependencies.
- [x] T008 Add a cached `_intake_lifecycle_service()` factory to
  `P2PWorkspace`.

## Phase 3 - Runtime Extraction

- [x] T009 Move intake ID allocation and intake directory lookup into the
  service.
- [x] T010 Move intake prompt creation into the service and delegate
  `P2PWorkspace.create_intake_prompt(...)`.
- [x] T011 Move intake import into the service and delegate
  `P2PWorkspace.import_intake(...)`.
- [x] T012 Move intake status listing into the service and delegate
  `P2PWorkspace.intake_statuses(...)`.
- [x] T013 Move apply-plan action metadata into the service.
- [x] T014 Move apply-plan creation into the service and delegate
  `P2PWorkspace.create_intake_apply_plan(...)`.
- [x] T015 Move apply-plan show into the service and delegate
  `P2PWorkspace.show_intake_apply_plan(...)`.
- [x] T016 Move apply action execution into the service and delegate
  `P2PWorkspace.run_intake_apply_action(...)`.
- [x] T017 Remove obsolete inline intake lifecycle helpers from
  `storage/filesystem.py`.
- [x] T018 Confirm CLI, MCP, next-action, and context modules do not import
  `IntakeLifecycleService` directly.

## Phase 4 - Tests

- [x] T019 Add direct service tests for prompt/status.
- [x] T020 Add direct service tests for import from file and directory.
- [x] T021 Add direct service tests for apply plan/show.
- [x] T022 Add direct service tests for `add_contribution` apply action.
- [x] T023 Add direct service tests for `open_choice` apply action.
- [x] T024 Add direct service tests for unsupported/governance-only and invalid
  payload error paths.
- [x] T025 Run focused CLI intake tests.
- [x] T026 Run focused MCP intake tests.
- [x] T027 Run focused next-action intake tests when applicable.
- [x] T028 Run full test suite.
- [x] T029 Run `.venv/bin/p2p validate`.
- [x] T030 Update the central refactoring status tracker.

## Current Progress

- Runtime extraction completed locally.
- Focused service, CLI, and MCP intake tests pass.
- No dedicated next-action intake test exists; next-action intake integration
  remains covered by full-suite tests.
- Full suite passes with 313 tests.
- `.venv/bin/p2p validate` passes with 0 findings.
