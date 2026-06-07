# MCP Registry Domain Catalog Split Tasks

## Tasks

### Phase 1 - Baseline Safety

- [x] T001: Capture the current public registry output through
  `tool_definitions()` in a regression test fixture or assertion helper;
  completion is a test that fails on name/order/schema drift.
- [x] T002: Add explicit assertions for `TOOL_NAMES` order matching
  `[definition["name"] for definition in tool_definitions()]`.
- [x] T003: Run the existing MCP registry tests before code movement;
  completion is recorded passing output.

### Phase 2 - Catalog Package Skeleton

- [x] T004: Create `src/p2p_engine/mcp/catalog/__init__.py` with no runtime side
  effects.
- [x] T005: Create `src/p2p_engine/mcp/catalog/common.py` and move the schema
  helper there.
- [x] T006: Update `mcp.registry` to use the shared catalog schema helper while
  preserving current output.
- [x] T007: Run focused MCP registry tests.

### Phase 3 - Prompt Catalog Extraction

- [x] T008: Create `src/p2p_engine/mcp/catalog/prompts.py`.
- [x] T009: Move `PROMPT_TOOL_KINDS` and prompt definition generation into the
  prompt catalog module, preserving `p2p_spec_prompt` placement.
- [x] T010: Keep any backward-compatible imports or constants in `mcp.registry`
  if tests or public imports require them.
- [x] T011: Run focused MCP registry and prompt-related MCP tests.

### Phase 4 - Maintenance And Project Catalog Extraction

- [x] T012: Create `src/p2p_engine/mcp/catalog/maintenance.py` for bootstrap,
  validation, context, registry, and assessment setup definitions.
- [x] T013: Create `src/p2p_engine/mcp/catalog/project.py` for project state,
  remote profile, rubrics, maturity, permissions, and consent read/write-safe
  definitions that are not collaboration branch flows.
- [x] T014: Replace the corresponding inline dictionaries in `mcp.registry`
  with imported ordered groups.
- [x] T015: Run focused MCP registry, maintenance handler, and project handler
  tests.

### Phase 5 - Proposal Catalog Extraction

- [x] T016: Create `src/p2p_engine/mcp/catalog/proposals.py`.
- [x] T017: Move proposal create/update/list/show, contribution, readiness,
  choice, conflict status, impact prompt, and intake definition groups as
  appropriate while preserving current order.
- [x] T018: Keep `ContributionType` enum usage local to the catalog module or
  an explicit helper; do not duplicate enum values by hand.
- [x] T019: Run focused MCP registry and proposal handler tests.

### Phase 6 - Collaboration Catalog Extraction

- [x] T020: Create `src/p2p_engine/mcp/catalog/collaboration.py`.
- [x] T021: Move sync, proposal draft commit, proposal branch, publish,
  request-review, accept/reject/defer, branch accept/reject, merge, finalize,
  cleanup, and branch scan definitions.
- [x] T022: Preserve all permission/consent wording in descriptions.
- [x] T023: Run focused MCP registry and collaboration handler tests.

### Phase 7 - Work And Spec Catalog Extraction

- [x] T024: Create `src/p2p_engine/mcp/catalog/work_specs.py`.
- [x] T025: Move Change Set, software spec, spec export, Work planning/list/show,
  and related prompt/export validation definitions.
- [x] T026: Run focused MCP registry and Work/spec handler tests.

### Phase 8 - Registry Assembly Cleanup

- [x] T027: Reduce `mcp.registry` to public exports, ordered assembly, and
  compatibility imports only.
- [x] T028: Verify that `mcp.tools.py` and `mcp/handlers/*` did not receive
  unrelated behavior changes.
- [x] T029: Update `specs/features/p2pworkspace-modular-refactoring-contract/refactoring-status.md`
  with the completed step and current line-count summary.

### Phase 9 - Verification

- [x] T030: Run focused tests:
  `tests/test_mcp_registry.py`, `tests/test_mcp_maintenance_handler.py`,
  `tests/test_mcp_project_handler.py`, `tests/test_mcp_proposal_handler.py`,
  `tests/test_mcp_collaboration_handler.py`, and
  `tests/test_mcp_work_spec_handler.py`.
- [x] T031: Run `.venv/bin/p2p validate`.
- [x] T032: Run the full test suite.
- [x] T033: Mark tasks complete only after evidence exists.

## Current Binding Status

All tasks are complete. Focused MCP tests, `.venv/bin/p2p validate`, and the
full test suite passed after the split.
