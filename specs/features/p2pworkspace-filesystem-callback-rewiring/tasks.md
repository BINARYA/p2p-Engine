# P2PWorkspace Filesystem Callback Rewiring Tasks

## Phase 1: Audit

- [x] T001 List remaining private callback wrappers in `storage.filesystem`.
- [x] T002 Identify service constructor call sites using those wrappers.
- [x] T003 Identify focused tests that still depend on wrapper callbacks.

## Phase 2: Rewiring

- [x] T004 Rewire validation callbacks to service-owned permission/proposal methods.
- [x] T005 Rewire proposal, change, software-spec, maturity, and branch callbacks to service-owned lookup methods.
- [x] T006 Rewire registry and project/spec export callbacks to `RegistryRecordBuilderService`.
- [x] T007 Rewire Work planning/branch callbacks to service-owned lookup methods.
- [x] T008 Update focused service tests to use service-owned collaborators.
- [x] T009 Remove private callback wrappers that have no remaining callers.

## Phase 3: Verification

- [x] T010 Run focused service tests for rewired dependencies.
- [x] T011 Run focused CLI/MCP regression tests for affected command surfaces.
- [x] T012 Run `p2p validate`.
- [x] T013 Run the full pytest suite.
- [x] T014 Update the refactoring status tracker.
