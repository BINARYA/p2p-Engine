# P2PWorkspace Work Planning Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Review current Work planning methods in `filesystem.py`; completion
  is a recorded scope covering create, statuses, summaries, show, id allocation,
  and directory lookup.

- [x] T002: Review Work helper functions and manifest shape; completion covers
  manifest payload, source proposal list, target validation, export validation,
  scanned registry inclusion, and next-action hints.

- [x] T003: Confirm out-of-scope boundaries; completion states that Work branch,
  retire, submit, review, publish, accept, finalize, cleanup, scan
  implementation, Git, sync, provider, CLI, and MCP remain outside the service.

- [x] T004: Capture mapped compatibility tests from `design.md`; completion is
  a command block ready to run after extraction.

## Phase 2 - Focused Tests First

- [x] T005: Add focused service test for Work plan creation and manifest shape.

- [x] T006: Add focused service test for unsupported handoff target rejection.

- [x] T007: Add focused service test for `show_work` detail mapping.

- [x] T008: Add focused service test for local Work statuses and summaries.

- [x] T009: Add focused service test for scanned Work status and summary
  inclusion.

- [x] T010: Add focused facade test proving `P2PWorkspace` Work planning
  methods delegate while preserving return attributes.

## Phase 3 - Service Extraction

- [x] T011: Create `src/p2p_engine/services/work_planning.py` with no Typer,
  Rich, MCP, JSON-RPC, Git adapter, sync, provider, or consent imports.

- [x] T012: Move Work planning dataclasses or compatible service-owned
  dataclasses into the service.

- [x] T013: Move Work manifest generation into the service.

- [x] T014: Move Work next-action calculation into the service.

- [x] T015: Move Work id allocation and directory lookup into the service.

- [x] T016: Move Work detail mapping into the service.

- [x] T017: Move Work status and summary mapping into the service.

- [x] T018: Wire a lazy `P2PWorkspace` Work planning service factory with the
  required callbacks.

- [x] T019: Delegate `P2PWorkspace` Work planning facade methods and private
  helper methods to the service.

## Phase 4 - Compatibility Verification

- [x] T020: Run focused Work planning service tests.

- [x] T021: Run mapped CLI Work planning tests.

- [x] T022: Run mapped MCP Work planning tests.

- [x] T023: Run `.venv/bin/p2p validate`.

- [x] T024: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T025: Review source scope with `git status --short` for this feature.

- [x] T026: Confirm no Work lifecycle, Git, sync, provider, consent, CLI
  formatting, or MCP formatting behavior moved into the service.

- [x] T027: Update `requirements.md` statuses after tests and validation pass.

- [x] T028: Record implementation evidence in `design.md`.

- [x] T029: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_work_planning_service.py
# 4 passed

.venv/bin/pytest tests/test_work_planning_service.py tests/test_cli.py::test_cli_work_plan_list_and_show tests/test_mcp.py::test_mcp_write_safe_spec_export_and_work_flow
# 6 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 180 passed
```
