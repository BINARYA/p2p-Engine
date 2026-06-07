# P2PWorkspace Project Assessment Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Review current project assessment methods in `filesystem.py`;
  completion covers refresh, show, compute, payload shape, and maturity
  inclusion.

- [x] T002: Review assessment dependencies; completion covers validate,
  registry status, proposal summaries, choices, changes, Work summaries,
  project state status, next actions, and maturity show callback.

- [x] T003: Confirm out-of-scope boundaries; completion states that maturity
  computation, rubrics, project-state refresh, registry generation, context,
  intake, Git/sync, CLI, and MCP remain outside the service.

- [x] T004: Capture mapped compatibility tests from `design.md`; completion is
  a command block ready to run after extraction.

## Phase 2 - Focused Tests First

- [x] T005: Add focused service test for draft-only project assessment scoring,
  gaps, suggested actions, and confidence.

- [x] T006: Add focused service test for validation-error blocked status and
  stale registry confidence.

- [x] T007: Add focused service test for maturity status/score inclusion when
  maturity file exists.

- [x] T008: Add focused service test for refresh writing the existing
  `assessment.yml` payload shape.

- [x] T009: Add focused service test for show parsing defaults and missing file
  error.

- [x] T010: Add focused facade test proving `P2PWorkspace` assessment methods
  delegate while preserving return attributes.

## Phase 3 - Service Extraction

- [x] T011: Create `src/p2p_engine/services/project_assessment.py` with no
  Typer, Rich, MCP, JSON-RPC, Git, sync, rubrics, maturity computation, context,
  intake, or lifecycle imports.

- [x] T012: Move project assessment dataclass or compatible service-owned
  dataclass into the service.

- [x] T013: Move deterministic assessment computation into the service.

- [x] T014: Move assessment payload generation into the service.

- [x] T015: Move assessment refresh write behavior into the service.

- [x] T016: Move assessment show/read parsing into the service.

- [x] T017: Wire a lazy `P2PWorkspace` project assessment service factory with
  the required callbacks.

- [x] T018: Delegate `P2PWorkspace` assessment facade methods to the service.

## Phase 4 - Compatibility Verification

- [x] T019: Run focused project assessment service tests.

- [x] T020: Run mapped CLI assessment tests.

- [x] T021: Run mapped MCP assessment tests.

- [x] T022: Run `.venv/bin/p2p validate`.

- [x] T023: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T024: Review source scope with `git status --short` for this feature.

- [x] T025: Confirm no maturity computation, rubrics, project-state refresh,
  registry generation, context packet, intake, Git/sync, lifecycle, CLI
  formatting, or MCP formatting moved into the service.

- [x] T026: Update `requirements.md` statuses after tests and validation pass.

- [x] T027: Record implementation evidence in `design.md`.

- [x] T028: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_project_assessment_service.py
# 5 passed

.venv/bin/pytest tests/test_cli.py::test_cli_assess_refresh_and_show tests/test_cli.py::test_cli_assess_show_requires_refresh tests/test_mcp.py::test_mcp_assess_refresh_and_show
# 3 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 193 passed
```
