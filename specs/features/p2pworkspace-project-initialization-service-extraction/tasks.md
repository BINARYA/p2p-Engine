# P2PWorkspace Project Initialization Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `filesystem.py` after agent template extraction and
  identify `init_project()` as the remaining runtime bootstrap concentration.

- [x] T002: Select project initialization as the next extraction because agent
  orchestration/templates, maturity, validation, registries, permissions,
  readiness, and remote profile behavior are already service-backed.

- [x] T003: Map consumers: direct workspace calls, CLI init/wizard, MCP
  `p2p_init_project`, skeleton tests, remote profile tests, domain/rubric tests,
  and agent bootstrap tests.

- [x] T004: Define out-of-scope boundaries: no CLI/MCP formatting, no generated
  payload changes, no Git/sync, no registry lifecycle, no validation, no
  proposal lifecycle, no agent renderer changes.

## Phase 2 - Focused Tests First

- [x] T005: Add direct service test for default initialization creating core
  files, directories, readiness profile, and default agent files.

- [x] T006: Add direct service test for software domain initialization omitting
  domain next actions and creating template rubrics.

- [x] T007: Add direct service test for unresolved/custom domain initialization
  creating domain next actions and rubric_missing setup.

- [x] T008: Add direct service test for owner permissions and remote/cloud
  profile payload.

- [x] T009: Add direct service test for idempotency: existing bootstrap files
  are not overwritten and duplicate created paths are not returned.

## Phase 3 - Service Extraction

- [x] T010: Create `src/p2p_engine/services/project_initialization.py` with no
  Typer, Rich, MCP, JSON-RPC, Git/sync, branch lifecycle, validation, registry,
  proposal lifecycle, maturity computation, or CLI formatting imports.

- [x] T011: Move bootstrap file assembly and idempotent write behavior into
  `ProjectInitializationService`.

- [x] T012: Move proposals/prompts directory creation into the service.

- [x] T013: Move final agent instruction refresh merge into the service using a
  callback.

- [x] T014: Add a lazy `P2PWorkspace` project initialization service factory
  with all required payload and normalization callbacks.

- [x] T015: Delegate `P2PWorkspace.init_project()` to the service.

## Phase 4 - Compatibility Verification

- [x] T016: Run focused project initialization service tests.

- [x] T017: Run focused CLI init/wizard tests.

- [x] T018: Run focused MCP init/project bootstrap tests.

- [x] T019: Run skeleton tests.

- [x] T020: Run `.venv/bin/p2p validate`.

- [x] T021: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T022: Review source scope with `git status --short`.

- [x] T023: Confirm no CLI/MCP formatting, generated payload, Git/sync,
  validation, registry lifecycle, proposal lifecycle, maturity, or agent
  renderer behavior changed.

- [x] T024: Update `requirements.md` statuses after tests and validation pass.

- [x] T025: Record implementation evidence in `design.md`.

- [x] T026: Update the global refactoring tracker.

- [x] T027: Mark all tasks complete only after evidence exists.

## Current Status

Completed.
