# P2PWorkspace Project Context Renderer Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `filesystem.py` after context packet extraction.

- [x] T002: Select intake/project brief context rendering as the next bounded
  extraction because it is read-only and already used as callbacks by services.

- [x] T003: Map consumers: `IntakeLifecycleService.create_prompt()`,
  `ProjectStateService.create_brief_prompt()`, CLI project brief/intake
  commands, and MCP project/work-spec handlers.

- [x] T004: Define out-of-scope boundaries: no intake recommendation changes,
  no project state refresh/import changes, no registry generation changes, no
  CLI/MCP formatting changes.

## Phase 2 - Focused Tests First

- [x] T005: Add direct renderer service test for intake context registry
  sections, missing registry fallback, empty registry fallback, and project
  overview inclusion.

- [x] T006: Add direct renderer service test for project brief context registry
  sections, project file inclusion, and intake status inclusion.

- [x] T007: Add direct renderer service test for changes included proposal list
  formatting and selected choice formatting.

## Phase 3 - Service Extraction

- [x] T008: Create `src/p2p_engine/services/project_contexts.py` with renderer
  service, protocols, and local read helper.

- [x] T009: Move intake context rendering into the service.

- [x] T010: Move project brief context rendering into the service.

- [x] T011: Add lazy `P2PWorkspace` project context renderer service factory.

- [x] T012: Wire `ProjectStateService` to
  `ProjectContextRendererService.render_project_brief_context`.

- [x] T013: Wire `IntakeLifecycleService` to
  `ProjectContextRendererService.render_intake_context`.

- [x] T014: Remove now-unused `_intake_context()` and
  `_project_brief_context()` from `storage/filesystem.py`.

## Phase 4 - Compatibility Verification

- [x] T015: Run focused project context renderer service tests.

- [x] T016: Run project state service tests.

- [x] T017: Run intake lifecycle service tests.

- [x] T018: Run focused CLI brief/intake tests.

- [x] T019: Run focused MCP brief/intake tests.

- [x] T020: Run `.venv/bin/p2p validate`.

- [x] T021: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T022: Review source scope with `git status --short`.

- [x] T023: Confirm no CLI/MCP formatting, project state refresh/import,
  intake apply, registry generation, Git/sync, or prompt output path behavior
  changed.

- [x] T024: Update `requirements.md` statuses after verification.

- [x] T025: Record implementation evidence in `design.md`.

- [x] T026: Update the global refactoring tracker.

- [x] T027: Mark all tasks complete only after evidence exists.

## Current Status

Completed.
