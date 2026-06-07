# P2PWorkspace Next Actions Service Extraction Tasks

## Phase 1 - Baseline And Scope

- [x] T001 Record current next-action public methods and private helpers in
  `storage/filesystem.py`.
- [x] T002 Record current CLI, MCP, project-status, context, and assessment
  consumers.
- [x] T003 Run focused baseline tests for next-action behavior before code
  movement.

## Phase 2 - Service Skeleton

- [x] T004 Add `src/p2p_engine/services/next_actions.py`.
- [x] T005 Move or recreate the `NextAction` dataclass in the service module.
- [x] T006 Import and re-export `NextAction` from
  `p2p_engine.storage.filesystem` for compatibility.
- [x] T007 Add `NextActionService` constructor with `root`, `p2p_dir`, and
  explicit project-state dependency callables.
- [x] T008 Add a cached `_next_action_service()` factory to `P2PWorkspace`.

## Phase 3 - Curated Lifecycle Extraction

- [x] T009 Move next-action path resolution into the service.
- [x] T010 Move curated payload read/write behavior into the service.
- [x] T011 Move record-to-model conversion and record normalization into the
  service.
- [x] T012 Move curated ID allocation into the service.
- [x] T013 Implement service `add(...)` and delegate
  `P2PWorkspace.next_action_add(...)`.
- [x] T014 Implement service `complete(...)` and `retire(...)` through shared
  close behavior, then delegate `P2PWorkspace` methods.
- [x] T015 Implement service `refresh(...)` and delegate
  `P2PWorkspace.next_actions_refresh(...)`.

## Phase 4 - Generated Actions Extraction

- [x] T016 Move active curated action loading into the service.
- [x] T017 Move deduplication into the service.
- [x] T018 Move fallback generation into the service while preserving existing
  order and command text.
- [x] T019 Move active choice blocker generation into the service.
- [x] T020 Implement service `list(limit=None)` and delegate
  `P2PWorkspace.next_actions(...)`.

## Phase 5 - Cleanup

- [x] T021 Remove obsolete private next-action helpers from
  `storage/filesystem.py`.
- [x] T022 Confirm `storage/filesystem.py` no longer imports `date` or `re`
  solely for removed next-action logic.
- [x] T023 Confirm no CLI or MCP module imports `NextActionService` directly.
- [x] T024 Update the refactoring status tracker from planned/in-progress to
  done when implementation and tests are complete.

## Phase 6 - Tests

- [x] T025 Add direct service tests for curated add/list behavior.
- [x] T026 Add direct service tests for complete/retire audit-log behavior.
- [x] T027 Add direct service tests for refresh normalization.
- [x] T028 Add direct service tests for generated fallback priority and
  deduplication.
- [x] T029 Add direct service tests for active choice blocker generation.
- [x] T030 Add direct service tests for invalid `next-actions.yml` and
  `next-actions-log.yml` shapes.
- [x] T031 Run focused CLI next-action tests.
- [x] T032 Run focused MCP next-action tests.
- [x] T033 Run full test suite.
- [x] T034 Run `.venv/bin/p2p validate`.

## Current Progress

- Runtime extraction completed locally.
- Focused service, CLI, and MCP tests pass.
- Full suite passes with 299 tests.
- `.venv/bin/p2p validate` passes with 0 findings.
