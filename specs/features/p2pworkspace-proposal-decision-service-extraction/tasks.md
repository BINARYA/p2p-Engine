# P2PWorkspace Proposal Decision Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Review current `P2PWorkspace.record_decision`; completion is a
  recorded method scope covering decision markdown, proposal status mutation,
  return dataclass, and proposal directory lookup.

- [x] T002: Confirm out-of-scope boundaries; completion states that readiness
  checks, consent, MCP audit, branch lifecycle, Git, registry, and project state
  remain outside the service.

- [x] T003: Capture mapped compatibility tests from `design.md`; completion is
  a command block ready to run after extraction.

## Phase 2 - Focused Tests First

- [x] T004: Add focused service test for recording an accepted decision and
  writing the existing `decision.md` section shape.

- [x] T005: Add focused service test for proposal `## Status` mutation.

- [x] T006: Add focused service test for rejected/deferred outcomes preserving
  `DecisionOutcome` values and approver/reason metadata.

- [x] T007: Add focused facade test proving `P2PWorkspace.record_decision`
  delegates while preserving return fields.

## Phase 3 - Service Extraction

- [x] T008: Create `src/p2p_engine/services/proposal_decisions.py` with no
  Typer, Rich, MCP, JSON-RPC, Git, registry, or project-state imports.

- [x] T009: Move proposal decision markdown generation into the service.

- [x] T010: Move proposal status update into the service using shared markdown
  helpers.

- [x] T011: Return the existing `Decision` dataclass from the service.

- [x] T012: Wire a lazy `P2PWorkspace` proposal decision service factory using
  root, p2p_dir, and proposal directory lookup.

- [x] T013: Delegate `P2PWorkspace.record_decision` to the service.

## Phase 4 - Compatibility Verification

- [x] T014: Run focused proposal decision service tests.

- [x] T015: Run mapped CLI decision tests.

- [x] T016: Run mapped MCP proposal decision tests.

- [x] T017: Run `.venv/bin/p2p validate`.

- [x] T018: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T019: Review source scope with `git status --short` for this feature.

- [x] T020: Confirm no readiness, consent, branch, Git, registry, project-state,
  CLI formatting, or MCP formatting behavior moved into the service.

- [x] T021: Update `requirements.md` statuses after tests and validation pass.

- [x] T022: Record implementation evidence in `design.md`.

- [x] T023: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_proposal_decision_service.py tests/test_cli.py::test_cli_import_exploration_file_and_record_decision tests/test_cli.py::test_cli_proposal_decision_shortcuts tests/test_mcp.py::test_mcp_draft_proposal_decision_requires_granted_consent tests/test_mcp.py::test_mcp_draft_proposal_accept_and_defer_consume_matching_consent
# 7 passed

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 176 passed
```
