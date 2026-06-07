# P2PWorkspace Permissions Consent Service Extraction Tasks

## Phase 1 - Preparation

- [x] T001: Review the current permission and consent implementation in
  `src/p2p_engine/storage/filesystem.py`; completion is a note identifying
  exact methods/helpers to move and helpers to leave behind.

- [x] T002: Review MCP consent audit usage in `src/p2p_engine/mcp/tools.py`;
  completion is confirmation that audit helpers will continue calling
  `P2PWorkspace` facade methods.

- [x] T003: Capture current compatibility test list from this feature design;
  completion is a test command block ready to run before and after extraction.

## Phase 2 - Focused Tests First

- [x] T004: Add focused permission service tests for owner default payload,
  actor id normalization, role normalization, actor kind normalization, policy
  read/synthesize, and actor add/update behavior.

- [x] T005: Add focused consent service tests for consent id allocation,
  operation/id normalization, receipt mapping, request/grant/show/status,
  revoke, validate, consume, and used-with-error behavior.

- [x] T006: Add focused negative-path consent tests for requested-not-
  authorized, actor mismatch without consume, operation mismatch, target
  mismatch, expired receipt mutation, consumed receipt rejection, revoked
  receipt rejection, and used-with-error receipt rejection.

## Phase 3 - Permission Service Extraction

- [x] T007: Create `src/p2p_engine/services/permissions.py`; completion is a
  service with no Typer, Rich, or MCP imports.

- [x] T008: Move permission policy path/default payload/read/write behavior to
  the permission service while preserving `.p2p/project/permissions.yml`.

- [x] T009: Move actor id, role, and actor kind normalization to the permission
  service or a minimal helper owned by it.

- [x] T010: Delegate `P2PWorkspace.permissions_show` and
  `P2PWorkspace.permissions_actor_add` to the permission service.

- [x] T011: Update project initialization to obtain the same default
  permissions payload through the new service boundary.

## Phase 4 - Consent Service Extraction

- [x] T012: Create `src/p2p_engine/services/consent.py`; completion is a
  service with no Typer, Rich, MCP, Git, or audit imports.

- [x] T013: Move consent path, id allocation, consent operation normalization,
  consent id normalization, and receipt mapping into the consent service.

- [x] T014: Move consent grant/request/show/status/revoke behavior into the
  consent service while preserving receipt YAML layout.

- [x] T015: Move consent validate/consume/used-with-error behavior into the
  consent service while preserving validation and transition semantics.

- [x] T016: Delegate all `P2PWorkspace` consent methods to the consent service.

- [x] T017: Confirm MCP audit helpers still call facade methods and were not
  folded into the consent service.

## Phase 5 - Compatibility Verification

- [x] T018: Run focused permission/consent service tests; completion is reviewed
  passing output.

- [x] T019: Run mapped CLI permission/consent tests; completion is reviewed
  passing output.

- [x] T020: Run mapped MCP permission/consent and permission-gated operation
  tests; completion is reviewed passing output.

- [x] T021: Run `.venv/bin/p2p validate`; completion is reviewed output with no
  errors.

## Phase 6 - Traceability And Completion

- [x] T022: Review `git diff` for source scope; completion confirms changes are
  limited to services, facade delegation, focused tests, and unavoidable imports.

- [x] T023: Update this feature's `requirements.md` statuses only after tests
  and validation pass.

- [x] T024: Record implementation evidence in `design.md`; completion lists
  facade methods delegated, helpers moved, helpers left in place, tests run,
  and remaining gaps.

- [x] T025: Mark tasks complete only with evidence; completion is all checked
  tasks backed by source diff, test output, validation output, or design notes.

## Current Status

Runtime extraction is complete for this feature. Focused service tests, mapped
CLI/MCP compatibility tests, and `.venv/bin/p2p validate` pass.
