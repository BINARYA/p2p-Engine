# P2PWorkspace Choice Lifecycle Service Extraction Tasks

## Phase 1 - Baseline And Scope

- [x] T001 Record current choice public methods and private helpers in
  `storage/filesystem.py`.
- [x] T002 Record current CLI, MCP, next-action, context, and assessment
  consumers.
- [x] T003 Run focused baseline tests for choice behavior before code movement.

## Phase 2 - Service Skeleton

- [x] T004 Add `src/p2p_engine/services/choices.py`.
- [x] T005 Move or recreate `ChoiceStatus`, `ChoiceDetail`, and
  `ChoiceDiscoveryFinding` in the service module.
- [x] T006 Import and re-export choice dataclasses from
  `p2p_engine.storage.filesystem` for compatibility.
- [x] T007 Add `ChoiceLifecycleService` constructor with `root`, `p2p_dir`,
  `find_proposal_dir`, `find_change_dir`, and `choice_registry_records`
  dependencies.
- [x] T008 Add a cached `_choice_lifecycle_service()` factory to
  `P2PWorkspace`.

## Phase 3 - Runtime Extraction

- [x] T009 Move choice ID allocation and choice directory lookup into the
  service.
- [x] T010 Move choice artifact creation into the service and delegate
  `P2PWorkspace.create_choice(...)`.
- [x] T011 Move choice status listing into the service and delegate
  `P2PWorkspace.choice_statuses(...)`.
- [x] T012 Move choice detail loading into the service and delegate
  `P2PWorkspace.show_choice(...)`.
- [x] T013 Move advisory choice discovery into the service and delegate
  `P2PWorkspace.discover_choices(...)`.
- [x] T014 Move blocker record/update behavior into the service and delegate
  `P2PWorkspace.block_choice(...)`.
- [x] T015 Move unblock behavior into the service and delegate
  `P2PWorkspace.unblock_choice(...)`.
- [x] T016 Move decision behavior into the service and delegate
  `P2PWorkspace.decide_choice(...)`.
- [x] T017 Remove obsolete inline choice lifecycle helpers from
  `storage/filesystem.py`.
- [x] T018 Confirm CLI, MCP, next-action, and assessment modules do not import
  `ChoiceLifecycleService` directly.

## Phase 4 - Tests

- [x] T019 Add direct service tests for create/list/show.
- [x] T020 Add direct service tests for advisory discovery.
- [x] T021 Add direct service tests for block/unblock.
- [x] T022 Add direct service tests for decide.
- [x] T023 Add direct service tests for invalid option, target type,
  `links.yml`, and `options.yml` error paths.
- [x] T024 Run focused CLI choice tests.
- [x] T025 Run focused MCP choice tests.
- [x] T026 Run focused next-action choice blocker tests.
- [x] T027 Run full test suite.
- [x] T028 Run `.venv/bin/p2p validate`.
- [x] T029 Update the central refactoring status tracker.

## Current Progress

- Runtime extraction completed locally.
- Focused service, CLI, MCP, and next-action choice tests pass.
- Full suite passes with 308 tests.
- `.venv/bin/p2p validate` passes with 0 findings.
