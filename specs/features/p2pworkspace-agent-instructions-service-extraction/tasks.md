# P2PWorkspace Agent Instructions Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess remaining `filesystem.py` runtime concentrations after
  project maturity extraction.

- [x] T002: Select agent instructions/integrations as the next extraction
  because it is cohesive and less foundational than project initialization.

- [x] T003: Map consumers: project initialization, CLI agent commands, MCP agent
  tools, and doctor integration checks.

- [x] T004: Define out-of-scope boundaries: no full project bootstrap, no CLI/MCP
  formatting, no Git/sync, no registry generation, no proposal lifecycle, no
  validation, no maturity/rubrics.

## Phase 2 - Focused Tests First

- [x] T005: Add direct service test for refreshing Codex instructions and
  merging profiles into `.p2p/agent-policy.yml`.

- [x] T006: Add direct service test for listing/showing integration registry
  status including drift fields.

- [x] T007: Add direct service test for install/update force and drift skip
  behavior.

- [x] T008: Add direct service test for uninstall safeguards and shared-file
  preservation.

## Phase 3 - Service Extraction

- [x] T009: Create `src/p2p_engine/services/agent_instructions.py` with no Typer,
  Rich, MCP, JSON-RPC, Git, sync, branch lifecycle, validation, registry,
  proposal lifecycle, or maturity imports.

- [x] T010: Move `AgentInstructionsResult` and `AgentIntegrationResult` into the
  service module.

- [x] T011: Move file maps, registry builders, drift helpers, and
  refresh/list/show/install/update/uninstall orchestration into the service
  module; keep template renderers as compatibility callbacks for this slice.

- [x] T012: Move refresh/list/show/install/update/uninstall behavior into
  `AgentInstructionService`.

- [x] T013: Add a lazy `P2PWorkspace` agent instruction service factory with
  project/repository callbacks.

- [x] T014: Delegate `P2PWorkspace` public agent methods and compatibility helper
  methods to the service.

- [x] T015: Keep `init_project()` calling the public facade and not owning agent
  generation internals.

## Phase 4 - Compatibility Verification

- [x] T016: Run focused agent instruction service tests.

- [x] T017: Run focused CLI agent/wizard tests.

- [x] T018: Run focused MCP agent tests.

- [x] T019: Run `.venv/bin/p2p validate`.

- [x] T020: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T021: Review source scope with `git status --short`.

- [x] T022: Confirm no project bootstrap, CLI/MCP formatting, Git/sync,
  validation, registry generation, proposal lifecycle, or maturity behavior
  moved into the service.

- [x] T023: Update `requirements.md` statuses after tests and validation pass.

- [x] T024: Record implementation evidence in `design.md`.

- [x] T025: Update the global refactoring tracker.

- [x] T026: Mark all tasks complete only after evidence exists.

## Current Status

Implemented and verified.

Evidence:

```bash
.venv/bin/pytest tests/test_agent_instructions_service.py tests/test_cli.py -k "agent or wizard"
# 13 passed, 84 deselected

.venv/bin/pytest tests/test_mcp.py -k agent tests/test_mcp_maintenance_handler.py
# 3 passed, 45 deselected

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 330 passed
```
