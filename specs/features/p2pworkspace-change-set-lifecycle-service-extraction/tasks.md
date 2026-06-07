# P2PWorkspace Change Set Lifecycle Service Extraction Tasks

## Phase 1 - Baseline And Scope

- [x] T001 Record current Change Set public methods and private helpers in
  `storage/filesystem.py`.
- [x] T002 Record current CLI, MCP, software-spec, spec-export, work-planning,
  registry, assessment, and next-action consumers.
- [x] T003 Run focused baseline tests for Change Set behavior before code
  movement.

## Phase 2 - Service Skeleton

- [x] T004 Add `src/p2p_engine/services/changes.py`.
- [x] T005 Move or recreate `ChangeSetStatus`, `ChangeSetPolicy`,
  `ChangeSetDetail`, and `ChangeSetTaskView` in the service module.
- [x] T006 Move `CHANGE_STATUS_TRANSITIONS` into the service module.
- [x] T007 Import and re-export Change Set dataclasses from
  `p2p_engine.storage.filesystem` for compatibility.
- [x] T008 Add `ChangeSetLifecycleService` constructor with `root`, `p2p_dir`,
  and `find_proposal_dir`.
- [x] T009 Add a cached `_change_set_lifecycle_service()` factory to
  `P2PWorkspace`.

## Phase 3 - Runtime Extraction

- [x] T010 Move Change Set ID allocation and directory lookup into the service.
- [x] T011 Move Change Set markdown and metadata-only git policy helpers into
  the service.
- [x] T012 Move Change Set creation into the service and delegate
  `P2PWorkspace.create_change_set(...)`.
- [x] T013 Move Change Set status listing into the service and delegate
  `P2PWorkspace.change_set_statuses(...)`.
- [x] T014 Move Change Set policy reading into the service and delegate
  `P2PWorkspace.change_set_policy(...)`.
- [x] T015 Move Change Set detail loading into the service and delegate
  `P2PWorkspace.show_change_set(...)`.
- [x] T016 Move status transition update into the service and delegate
  `P2PWorkspace.update_change_set_status(...)`.
- [x] T017 Move task/action reading into the service and delegate
  `P2PWorkspace.change_set_tasks(...)`.
- [x] T018 Delegate private compatibility `_find_change_dir(...)` to the
  service.
- [x] T019 Remove obsolete inline Change Set helpers from
  `storage/filesystem.py`.
- [x] T020 Confirm CLI, MCP, and dependent services do not import
  `ChangeSetLifecycleService` directly.

## Phase 4 - Tests

- [x] T021 Add direct service tests for create/show/status.
- [x] T022 Add direct service tests for policy and tasks/actions.
- [x] T023 Add direct service tests for valid/invalid status transitions.
- [x] T024 Add direct service tests for unaccepted proposal, invalid policy,
  invalid tasks, and missing Change Set error paths.
- [x] T025 Run focused CLI Change Set tests.
- [x] T026 Run focused MCP Change Set tests.
- [x] T027 Run affected service tests.
- [x] T028 Run full test suite.
- [x] T029 Run `.venv/bin/p2p validate`.
- [x] T030 Update the central refactoring status tracker.

## Current Progress

- Runtime extraction completed locally.
- Focused service, CLI, MCP, and dependent service tests pass.
- Full suite passes with 318 tests.
- `.venv/bin/p2p validate` passes with 0 findings.
