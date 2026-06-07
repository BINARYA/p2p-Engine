# P2PWorkspace Readiness Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Review current readiness methods in `filesystem.py`; completion is
  a recorded method list covering profile, read, write, override, refresh, and
  initialize.

- [x] T002: Review helper functions used by readiness scoring; completion is a
  recorded helper list covering default payload, validators, refresh payload,
  quality scoring, labels, uniqueness, and open-question counting.

- [x] T003: Confirm out-of-scope boundaries; completion states that proposal
  decisions, CLI/MCP formatting, registry generation, and next-action
  orchestration remain outside the service.

- [x] T004: Capture mapped compatibility tests from `design.md`; completion is
  a command block ready to run after extraction.

## Phase 2 - Focused Tests First

- [x] T005: Add focused service test for default readiness profile creation and
  mapping.

- [x] T006: Add focused service test for missing proposal readiness returning
  `not_assessed`.

- [x] T007: Add focused service test for write/read assessment payload
  compatibility.

- [x] T008: Add focused service test for refresh scoring with artifact quality
  caps, missing criteria, suggested next actions, and failed gates.

- [x] T009: Add focused service test for owner override metadata preservation.

- [x] T010: Add focused service test for initialization from proposal artifacts,
  including owner-question gate behavior.

## Phase 3 - Service Extraction

- [x] T011: Create `src/p2p_engine/services/readiness.py` with no Typer, Rich,
  MCP, Git, CLI, or governance decision imports.

- [x] T012: Move readiness dataclasses or compatible service-owned dataclasses
  into the service.

- [x] T013: Move default readiness profile payload generation into the service.

- [x] T014: Move readiness profile validation and profile mapping into the
  service.

- [x] T015: Move readiness assessment validation and assessment mapping into
  the service.

- [x] T016: Move read/write proposal readiness behavior into the service.

- [x] T017: Move owner override behavior into the service while preserving date
  fields and effective forced-ready fields.

- [x] T018: Move refresh/scoring helpers into the service while preserving
  computed score, labels, failed gates, missing, suggested next, and computed_at.

- [x] T019: Move initialize readiness artifact scanning into the service while
  preserving evidence artifacts and section names.

- [x] T020: Wire `P2PWorkspace` lazy factory for the readiness service using
  only root, p2p_dir, and proposal directory lookup.

- [x] T021: Delegate public readiness facade methods from `P2PWorkspace`.

## Phase 4 - Compatibility Verification

- [x] T022: Run focused readiness service tests.

- [x] T023: Run mapped skeleton readiness tests.

- [x] T024: Run mapped CLI readiness tests.

- [x] T025: Run mapped MCP readiness tests.

- [x] T026: Run `.venv/bin/p2p validate`.

- [x] T027: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T028: Review source scope with `git status --short` for this feature.

- [x] T029: Confirm no proposal decision, branch, Git, registry, or CLI/MCP
  formatting behavior moved into the service.

- [x] T030: Update `requirements.md` statuses after tests and validation pass.

- [x] T031: Record implementation evidence in `design.md`.

- [x] T032: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_readiness_service.py tests/test_skeleton.py::test_init_project_creates_default_readiness_profile tests/test_skeleton.py::test_missing_proposal_readiness_is_not_assessed tests/test_skeleton.py::test_write_and_read_proposal_readiness_assessment tests/test_skeleton.py::test_refresh_proposal_readiness_computes_score_with_artifact_caps tests/test_cli.py::test_cli_proposal_readiness_status_refresh_and_explain tests/test_cli.py::test_cli_proposal_accept_can_record_readiness_override tests/test_mcp.py::test_mcp_proposal_readiness_tools_are_advisory
# 9 passed

.venv/bin/pytest
# 173 passed
```
