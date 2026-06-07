# P2PWorkspace Project Maturity Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `storage/filesystem.py` after validation extraction and
  identify remaining runtime concentrations.

- [x] T002: Select maturity/rubrics as the next extraction because it is more
  isolated than project initialization and agent instruction generation.

- [x] T003: Map consumers: CLI project rubrics, CLI assess maturity, MCP
  maintenance/project handlers, and project assessment maturity inclusion.

- [x] T004: Define out-of-scope boundaries: no full project bootstrap, no agent
  instruction generation, no CLI/MCP formatting, no Git/sync, no registry
  generation, no branch lifecycle.

## Phase 2 - Focused Tests First

- [x] T005: Add direct service test for rubric initialization, domain file
  update, and project.yml domain update.

- [x] T006: Add direct service test for rubric preview being read-only.

- [x] T007: Add direct service test for maturity scoring using accepted
  proposal/decision evidence.

- [x] T008: Add direct service test for unresolved rubrics returning
  `rubric_missing` and score `0`.

## Phase 3 - Service Extraction

- [x] T009: Create `src/p2p_engine/services/project_maturity.py` with no Typer,
  Rich, MCP, JSON-RPC, Git, sync, branch lifecycle, validation, registry, or
  agent instruction imports.

- [x] T010: Move `ProjectRubrics` and `ProjectDefinitionMaturity` into the
  service module.

- [x] T011: Move rubric init, preview, and show behavior into
  `ProjectMaturityService`.

- [x] T012: Move maturity refresh, show, computation, payload generation, and
  evidence matching into `ProjectMaturityService`.

- [x] T013: Keep domain/rubric helper behavior compatible for `init_project()`
  until the bootstrap extraction happens.

- [x] T014: Add a lazy `P2PWorkspace` project maturity service factory with the
  required callbacks.

- [x] T015: Delegate `P2PWorkspace` maturity/rubrics facade methods to the
  service while preserving facade imports.

## Phase 4 - Compatibility Verification

- [x] T016: Run focused project maturity service tests.

- [x] T017: Run focused CLI maturity/rubrics/domain tests.

- [x] T018: Run focused MCP maturity/rubrics/domain tests.

- [x] T019: Run `.venv/bin/p2p validate`.

- [x] T020: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T021: Review source scope with `git status --short`.

- [x] T022: Confirm no project initialization, agent instruction generation,
  CLI/MCP formatting, Git/sync, registry generation, validation, or branch
  lifecycle behavior moved into the service.

- [x] T023: Update `requirements.md` statuses after tests and validation pass.

- [x] T024: Record implementation evidence in `design.md`.

- [x] T025: Update the global refactoring tracker.

- [x] T026: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_project_maturity_service.py
# 4 passed

.venv/bin/pytest tests/test_cli.py -k "maturity or rubrics or domain_template or default_domain"
# 3 passed, 90 deselected

.venv/bin/pytest tests/test_mcp.py -k "maturity or rubrics or custom_domain"
# 2 passed, 42 deselected

.venv/bin/pytest tests/test_mcp_maintenance_handler.py
# 4 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 326 passed
```
