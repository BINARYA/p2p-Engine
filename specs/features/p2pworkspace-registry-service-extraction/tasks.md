# P2PWorkspace Registry Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Review current registry facade methods in `filesystem.py`;
  completion covers refresh, status, show, duplicate guard, and expected files.

- [x] T002: Review registry record builder dependencies; completion confirms
  proposal/change/choice/relation/artifact/readiness builders remain outside the
  service for this slice.

- [x] T003: Confirm out-of-scope boundaries; completion states that project
  state, assessment, context, intake, CLI/MCP formatting, Git/sync, and lifecycle
  behavior remain outside the service.

- [x] T004: Capture mapped compatibility tests from `design.md`; completion is
  a command block ready to run after extraction.

## Phase 2 - Focused Tests First

- [x] T005: Add focused service test for refresh writing all registry files with
  existing top-level keys and source values.

- [x] T006: Add focused service test for stale status when files are missing.

- [x] T007: Add focused service test for status becoming fresh after refresh and
  stale after proposal/change count drift.

- [x] T008: Add focused service test for show success, unsupported registry
  error, missing file error, and invalid list-shape error.

- [x] T009: Add focused facade test proving `P2PWorkspace` registry methods
  delegate while preserving return attributes.

## Phase 3 - Service Extraction

- [x] T010: Create `src/p2p_engine/services/registries.py` with no Typer, Rich,
  MCP, JSON-RPC, Git, sync, project-state, intake, or lifecycle imports.

- [x] T011: Move registry dataclasses or compatible service-owned dataclasses
  into the service.

- [x] T012: Move registry filename/key/source mapping into the service.

- [x] T013: Move registry refresh file writing into the service.

- [x] T014: Move registry status and stale detection into the service.

- [x] T015: Move registry show validation and mapping into the service.

- [x] T016: Wire a lazy `P2PWorkspace` registry service factory with record
  builder callbacks.

- [x] T017: Delegate `P2PWorkspace.refresh_registries`, `registry_status`, and
  `show_registry` to the service.

## Phase 4 - Compatibility Verification

- [x] T018: Run focused registry service tests.

- [x] T019: Run mapped CLI registry tests.

- [x] T020: Run mapped MCP registry tests.

- [x] T021: Run `.venv/bin/p2p validate`.

- [x] T022: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T023: Review source scope with `git status --short` for this feature.

- [x] T024: Confirm no record builders, project-state, assessment, context,
  intake, Git/sync, lifecycle, CLI formatting, or MCP formatting behavior moved
  into the service.

- [x] T025: Update `requirements.md` statuses after tests and validation pass.

- [x] T026: Record implementation evidence in `design.md`.

- [x] T027: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_registry_service.py
# 4 passed

.venv/bin/pytest tests/test_cli.py::test_cli_registry_refresh_status_and_show tests/test_cli.py::test_cli_registry_refresh_rejects_duplicate_proposal_ids tests/test_mcp.py::test_mcp_registry_refresh_tool tests/test_mcp.py::test_mcp_change_project_registry_and_remote_read_tools
# 4 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 184 passed
```
