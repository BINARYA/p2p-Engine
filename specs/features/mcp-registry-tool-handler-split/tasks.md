# MCP Registry Tool Handler Split Tasks

## Phase 1 - Registry Extraction

- [x] T001 Create `src/p2p_engine/mcp/registry.py` for MCP declarations.
- [x] T002 Move `TOOL_NAMES` into `registry.py`.
- [x] T003 Move prompt tool kind mapping into `registry.py` as `PROMPT_TOOL_KINDS`.
- [x] T004 Move `_schema()`, prompt tool definition construction, and `tool_definitions()` into `registry.py`.
- [x] T005 Keep `src/p2p_engine/mcp/tools.py` as compatibility surface by importing and re-exporting registry declarations.
- [x] T006 Update prompt dispatch in `call_tool()` to use imported `PROMPT_TOOL_KINDS`.
- [x] T007 Add focused registry tests for tool-name/schema parity and prompt mapping availability.
- [x] T008 Run focused MCP tests, full pytest suite, and `p2p validate`.

## Phase 2 - Handler Grouping

- [x] T009 Inventory `call_tool()` branches by domain and target handler module.
- [x] T010 Extract read-only project/context/registry handlers.
- [x] T011 Extract proposal/readiness/decision handlers.
- [x] T012 Extract sync/consent/branch handlers.
- [x] T013 Extract spec/export/work/prompt handlers.
- [x] T014 Extract bootstrap, agent integration, maintenance, and next-action handlers.
- [x] T015 Keep `call_tool()` as the single dispatch facade until all handler modules are covered by tests.
- [x] T016 Run focused MCP lifecycle tests after each handler group extraction.

## Phase 3 - Final Verification

- [x] T017 Verify `tool_definitions()` still returns the same public names.
- [x] T018 Verify representative read-only and write-safe MCP tools still execute.
- [x] T019 Run full test suite.
- [x] T020 Run `p2p validate`.
- [x] T021 Update `refactoring-status.md`.
