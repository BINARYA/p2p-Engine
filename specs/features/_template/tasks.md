# Tasks - <feature-name>

- [ ] T001: Review relevant steering and feature specs; completion is a clear
  implementation boundary.
- [ ] T002: Confirm public surface and MCP impact; completion is a documented
  decision that MCP is not applicable, unchanged, implemented as read-only,
  implemented as write-safe, implemented as consent-gated, or explicitly
  deferred with rationale.
- [ ] T003: Update implementation files for R001; completion is behavior covered
  by focused tests.
- [ ] T004: Update tests for R001 and edge cases; completion is a passing focused
  test run.
- [ ] T005: Update MCP catalog/handler/docs/tests if the MCP parity decision
  requires MCP changes; completion is passing MCP-focused validation or an
  explicit not-applicable/deferred note.
- [ ] T006: Update docs if public behavior changes; completion is docs matching
  the implemented behavior.
- [ ] T007: Run focused validation; completion is the useful focused command
  recorded and reviewed.
- [ ] T008: Run public-contract validation if CLI, MCP, persistence, validation,
  Git, or generated artifacts can be externally observed; completion is the
  command output reviewed or an explicit not-applicable note.
- [ ] T009: Run full-suite validation before handoff; completion is the full
  command output reviewed or an explicit residual-risk note.
