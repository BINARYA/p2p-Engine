# P2PWorkspace Facade Final Reassessment Tasks

## Tasks

### Phase 1 - Runtime Surface Audit

- [x] T001: Measure the largest Python modules under `src/p2p_engine`; completion
  is a recorded table in `design.md`.
- [x] T002: Inspect `storage.filesystem` public methods and module-level helpers;
  completion is a classification of whether it remains an extraction candidate
  or an acceptable compatibility facade.
- [x] T003: Inspect `cli.py` and `cli_commands/*`; completion is a classification
  of root app assembly, command presentation modules, and any follow-up
  candidates.
- [x] T004: Inspect `mcp/tools.py`, `mcp/registry.py`, and `mcp/handlers/*`;
  completion is a classification of dispatch, schema/catalog, and handler
  responsibilities.

### Phase 2 - Refactoring Decision

- [x] T005: Decide whether the next step should modify runtime code now or
  produce a focused follow-up feature; completion is the decision in
  `design.md`.
- [x] T006: Identify the next recommended implementation feature; completion is
  a single focused target with explicit rationale.
- [x] T007: Preserve the rule that no runtime extraction starts without local
  requirements, design, and task checklist.

### Phase 3 - Tracker Update

- [x] T008: Add the reassessment to
  `specs/features/p2pworkspace-modular-refactoring-contract/refactoring-status.md`.
- [x] T009: Update the next recommended order so the owner can see what was done
  and what remains.

### Phase 4 - Verification

- [x] T010: Verify that this step changes only local development specs and the
  refactoring tracker; no runtime source change is required for the reassessment.
- [x] T011: Record that runtime tests are not required for this documentation
  reassessment step because no `src/` or `tests/` code is changed by it.

## Current Binding Status

All tasks are complete. The reassessment identifies `mcp/registry.py` as the
next focused refactoring candidate and intentionally leaves `P2PWorkspace` as
the compatibility facade.
