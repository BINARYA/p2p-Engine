# P2PWorkspace Project State Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Review current project-state facade methods in `filesystem.py`;
  completion covers refresh, status, show, brief prompt, brief import, and brief
  show.

- [x] T002: Review renderer and helper dependencies; completion covers project
  markdown renderers, feature markdown, brief prompt markdown, brief context,
  YAML validation, accepted proposals, registry status, and next actions.

- [x] T003: Confirm out-of-scope boundaries; completion states that assessment,
  maturity, rubrics, next-action lifecycle, registries, context packets, intake,
  Git/sync, CLI, and MCP remain outside the service.

- [x] T004: Capture mapped compatibility tests from `design.md`; completion is
  a command block ready to run after extraction.

## Phase 2 - Focused Tests First

- [x] T005: Add focused service test for project refresh artifact paths and
  generated file content.

- [x] T006: Add focused service test for feature artifact generation from
  accepted proposals.

- [x] T007: Add focused service test for project status and section/feature
  show behavior.

- [x] T008: Add focused service test for brief prompt path and context writes.

- [x] T009: Add focused service test for brief directory import, YAML validation,
  file import, show, and missing-source errors.

- [x] T010: Add focused facade test proving `P2PWorkspace` project-state methods
  delegate while preserving return attributes.

## Phase 3 - Service Extraction

- [x] T011: Create `src/p2p_engine/services/project_state.py` with no Typer,
  Rich, MCP, JSON-RPC, Git, sync, assessment, maturity, intake, or lifecycle
  imports.

- [x] T012: Move project-state dataclasses or compatible service-owned
  dataclasses into the service.

- [x] T013: Move project refresh artifact writing into the service.

- [x] T014: Move project section and feature show lookup into the service.

- [x] T015: Move project status mapping into the service.

- [x] T016: Move project brief prompt file writing into the service.

- [x] T017: Move project brief import/show behavior into the service.

- [x] T018: Wire a lazy `P2PWorkspace` project-state service factory with the
  required callbacks.

- [x] T019: Delegate `P2PWorkspace` project-state facade methods to the service.

## Phase 4 - Compatibility Verification

- [x] T020: Run focused project-state service tests.

- [x] T021: Run mapped CLI project-state tests.

- [x] T022: Run mapped MCP project-state tests.

- [x] T023: Run `.venv/bin/p2p validate`.

- [x] T024: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T025: Review source scope with `git status --short` for this feature.

- [x] T026: Confirm no assessment, maturity, rubrics, next-action lifecycle,
  registry generation, context packet, intake, Git/sync, CLI formatting, or MCP
  formatting moved into the service.

- [x] T027: Update `requirements.md` statuses after tests and validation pass.

- [x] T028: Record implementation evidence in `design.md`.

- [x] T029: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_project_state_service.py
# 4 passed

.venv/bin/pytest tests/test_cli.py::test_cli_project_refresh_status_and_show tests/test_cli.py::test_cli_project_brief_prompt_import_and_show tests/test_mcp.py::test_mcp_call_tool_reads_project_state tests/test_mcp.py::test_mcp_project_brief_prompt_and_show
# 4 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 188 passed
```
