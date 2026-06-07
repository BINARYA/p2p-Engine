# P2PWorkspace Agent Template Renderer Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `filesystem.py` after agent orchestration extraction and
  identify remaining agent template renderer concentration.

- [x] T002: Select agent template renderer relocation as the next extraction
  because it is lower risk than full project initialization extraction.

- [x] T003: Map consumers: `init_project()`, `AgentInstructionService`, CLI agent
  commands, MCP agent tools, and wizard/bootstrap tests.

- [x] T004: Define out-of-scope boundaries: no orchestration changes, no
  generated text changes, no CLI/MCP formatting, no Git/sync, no validation, no
  registry lifecycle, no project initialization extraction.

## Phase 2 - Focused Verification First

- [x] T005: Run or rely on existing direct agent service tests as renderer
  behavior contracts.

- [x] T006: Ensure focused CLI/MCP agent tests remain in the verification map.

## Phase 3 - Renderer Extraction

- [x] T007: Create `src/p2p_engine/services/agent_templates.py` with no runtime
  orchestration imports.

- [x] T008: Move adapter constants, profile normalization, profile expansion,
  adapter capabilities, instruction file map, adapter file map, policy payload,
  managed header, readiness gap block, and template renderers into the module.

- [x] T009: Wire `filesystem.py` to import the renderer functions and constants.

- [x] T010: Remove duplicate renderer definitions from `filesystem.py`.

- [x] T011: Keep `AgentInstructionService` unchanged except for receiving the
  imported callbacks from `P2PWorkspace`.

## Phase 4 - Compatibility Verification

- [x] T012: Run focused agent instruction service tests.

- [x] T013: Run focused CLI agent/wizard tests.

- [x] T014: Run focused MCP agent tests.

- [x] T015: Run `.venv/bin/p2p validate`.

- [x] T016: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T017: Review source scope with `git status --short`.

- [x] T018: Confirm no orchestration, generated text, CLI/MCP formatting,
  Git/sync, validation, registry lifecycle, or project initialization behavior
  changed.

- [x] T019: Update `requirements.md` statuses after tests and validation pass.

- [x] T020: Record implementation evidence in `design.md`.

- [x] T021: Update the global refactoring tracker.

- [x] T022: Mark all tasks complete only after evidence exists.

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
