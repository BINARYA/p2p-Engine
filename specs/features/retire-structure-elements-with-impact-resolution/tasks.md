# Tasks - Retire Structure Elements With Impact Resolution

## Inventory And Contracts

- [ ] T001 [R006-R019, D003-D004] Inventory every governed reference to
  sections and nested structure elements and classify active/history behavior.
- [ ] T002 [R001-R019, D001-D003] Define retirement impact, decision,
  disposition, collection and result contracts with stable IDs and bounds.
- [ ] T003 [R006-R012, D004-D005] Extend the project-memory reference index to
  prove completeness and produce readiness/classification impact inputs.

## Preview And Planning

- [ ] T004 [R006-R012, D002-D005] Implement one-snapshot impact analysis and
  first-preview output without writes.
- [ ] T005 [R013-R019, D002-D003] Implement strict disposition-plan parsing,
  semantic validation and complete second preview.
- [ ] T006 [R009-R011, N001-N003, D004-D005] Add bounds, truncation blockers and projected
  readiness/classification deltas.

## Atomic Apply

- [ ] T007 [R020-R025, D006] Implement deterministic candidate materialization
  for lifecycle, scope, question/evidence/artifact dispositions and event data.
- [ ] T008 [R020-R025, N004, D006-D007] Add atomic apply, receipt, mutation status, replay
  and workspace recovery integration.
- [ ] T009 [R026-R028, D001] Update active/history reads and publication models
  to preserve retired context.

## Public Surfaces

- [ ] T010 [R020-R025, D002, D005-D007] Add CLI preview/apply/status JSON and human summaries
  with exact plan input and stable error mapping.
- [ ] T011 [R020-R025, D002, D005-D007] Add MCP preview and consent-gated apply parity over the
  same services.
- [ ] T012 [AC007-AC008, D001-D007] Update CLI/MCP docs, primitive inventory, agent
  capabilities and generated guidance.

## Validation

- [ ] T013 [AC001-AC005, D001-D006] Add section, nested-element, historical, active,
  global, unassigned, unsupported-kind and last-criterion scenarios.
- [ ] T014 [AC005-AC008, D002-D007] Add truncation, stale source, divergent plan, replay,
  response-loss and fault-injection tests.
- [ ] T015 [N005, D004] Add bounded performance tests proving one indexed impact pass
  rather than repeated full scans.
- [ ] T016 [AC001-AC009, D001-D007] Run focused, public-contract, installed-wheel and full
  suite validation.
- [ ] T017 [R029-R030, D007, AC009] Integrate `project.structure.retire` authority into
  both previews, disposition apply and receipt/replay tests while keeping
  provider delegability outside core policy.
