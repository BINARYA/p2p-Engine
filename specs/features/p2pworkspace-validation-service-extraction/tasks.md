# P2PWorkspace Validation Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Locate current validation dataclasses and
  `P2PWorkspace.validate()` implementation in `filesystem.py`.

- [x] T002: Map validation consumers: CLI validate, MCP validate, skeleton
  validation, project assessment, and existing tests.

- [x] T003: Define out-of-scope boundaries: no CLI formatting, MCP formatting,
  registry generation, branch lifecycle, readiness computation, maturity, or
  rubrics move into this service.

- [x] T004: Capture compatibility verification commands in `design.md`.

## Phase 2 - Focused Tests First

- [x] T005: Add direct service test for a valid initialized workspace.

- [x] T006: Add direct service test for invalid YAML reporting
  `P2P010_INVALID_YAML`.

- [x] T007: Add direct service test for invalid permissions and/or consent
  receipt findings.

- [x] T008: Add direct service test for duplicate proposal ID or proposal
  structure findings.

## Phase 3 - Service Extraction

- [x] T009: Create `src/p2p_engine/services/validation.py` with no Typer, Rich,
  MCP, JSON-RPC, Git, sync, branch lifecycle, maturity, or assessment imports.

- [x] T010: Move `ValidationFinding` and `ValidationResult` into the validation
  service module.

- [x] T011: Move required-path and structured-YAML validation into
  `ValidationService`.

- [x] T012: Move readiness profile, readiness assessment, and agent integration
  payload validation into the service module.

- [x] T013: Move permissions and consent receipt validation into
  `ValidationService`.

- [x] T014: Move proposal directory, proposal document, decision status, and
  duplicate proposal ID checks into `ValidationService`.

- [x] T015: Move registry status stale/error checks into `ValidationService`.

- [x] T016: Add a lazy `P2PWorkspace` validation service factory with the
  required callbacks.

- [x] T017: Delegate `P2PWorkspace.validate()` to the validation service while
  preserving facade imports.

## Phase 4 - Compatibility Verification

- [x] T018: Run focused validation service tests.

- [x] T019: Run focused skeleton validation tests.

- [x] T020: Run focused CLI validation tests.

- [x] T021: Run focused MCP validation and project assessment validation tests.

- [x] T022: Run `.venv/bin/p2p validate`.

- [x] T023: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T024: Review source scope with `git status --short`.

- [x] T025: Confirm no CLI/MCP formatting, registry generation, branch
  lifecycle, readiness computation, maturity, rubrics, or project assessment
  behavior moved into the service.

- [x] T026: Update `requirements.md` statuses after tests and validation pass.

- [x] T027: Record implementation evidence in `design.md`.

- [x] T028: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_validation_service.py
# 4 passed

.venv/bin/pytest tests/test_skeleton.py -k validate
# 2 passed, 11 deselected

.venv/bin/pytest tests/test_cli.py -k validate
# 5 passed, 88 deselected

.venv/bin/pytest tests/test_mcp.py -k validate
# 2 passed, 42 deselected

.venv/bin/pytest tests/test_mcp_project_handler.py tests/test_project_assessment_service.py -k validation
# 1 passed, 7 deselected

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 322 passed
```
