# Tasks - Support Typed Authority Context In Governed Mutations

## Contract And Inventory

- [x] T001 [R001-R040, D001-D009] Inventory every receipt-backed governed
  mutation, actor/owner check, executor field, preview token, receipt, event,
  CLI option, MCP consent path and generated-agent instruction.
- [x] T002 [R007, R031-R035, D004] Publish the governed-capability registry and
  map every current and planned mutation to an explicit capability or reviewed
  read-only exemption.
- [x] T003 [R001-R015, D001-D003, D007] Define versioned project authority,
  subject, executor, claim, basis and `AuthorityContext` schemas with bounds and
  audit-safe projections.
- [x] T004 [R019, N003, D002-D003] Document the trust boundary: external attestations are
  provider claims, worker invocation must be protected and P2P performs no
  online provider verification.

## Core Authority Services

- [x] T005 [R001-R006, R015, R036-R037, D007-D008] Implement schema-4 authority
  descriptor persistence, local/external bootstrap, validation, neutral IDs and
  generation handling.
- [x] T006 [R007-R015, N001-N004, D001-D004] Implement strict context parsing,
  normalization, capability matching and local/external mode validation.
- [x] T007 [R016-R019, D002-D003] Adapt existing local actor/permission checks
  behind the local-policy resolver without importing hosted concepts.
- [x] T008 [R020-R025, N001, N005, D005] Bind canonical authority digest and
  safe evidence to preview, idempotency, transaction, receipt, event and status
  contracts.
- [x] T009 [R025, N006, D001-D005, D007, D009] Add stable typed errors and workspace diagnostics for
  invalid, stale, conflicting or legacy authority state.
- [x] T010 [R038-R040, D009] Implement `project.authority.rotate`
  preview/apply/status/replay with root-only local/external authority,
  atomic descriptor/event/receipt persistence and fault recovery.

## Proposal Decision Vertical Slice

- [x] T011 [R026-R030, D006] Refactor decision preview/apply to resolve
  `proposal.decide` through AuthorityContext while preserving local-owner
  behavior.
- [x] T012 [R027-R028, D001, D006] Persist delegated subject and actual executor separately
  in decision events, history, receipts and safe read models.
- [x] T013 [R029, D006] Require an additional root-authority
  `proposal.readiness.override` claim whenever decision apply overrides a
  readiness gate.
- [x] T014 [R020-R025, R026-R030, D005-D006] Update decision replay, status, recovery and
  divergent-key handling for exact authority evidence.

## CLI, MCP And Agent Surfaces

- [x] T015 [R008-R015, R020-R030, R038-R040, D001-D005, D009] Add safe typed CLI JSON input and output for
  authority context without exposing arbitrary provider payloads or secrets.
- [x] T016 [R026-R030, D001, D005-D006] Update MCP decision preview/apply and consent evidence to
  carry equivalent subject, executor and authority semantics.
- [x] T017 [R031-R040, D004, D007-D009] Expose capability metadata to maintained inventories and
  generated guidance without claiming unavailable mutation support.
- [x] T018 [AC007-AC008, AC010, D001-D009] Update CLI, MCP, architecture, security and standalone
  usage documentation, including the external-attestation limitation.

## Coordinated Feature Convergence

- [x] T019 [R031-R040, AC007, D004, D007-D009] Verify domain initialization/change, structure
  edit/classification/retirement/export/replacement/merge/restore and readiness
  specifications use the capability matrix and do not embed WaveKit roles.
- [x] T020 [R006, D007] Replace `wk-owner-*` fixtures and examples with neutral
  schema-4 project-authority identities; add no 0.4.x compatibility branch.

## Tests And Release Validation

- [x] T021 [AC001-AC006, AC009-AC010, D001-D009] Add local owner, delegated decision, root override,
  mode mismatch, stale generation, executor mismatch and secret-rejection tests.
- [x] T022 [AC004-AC005, AC010, N005, D005-D006, D009] Add response-loss, revocation-after-apply,
  authorization-before-start, exact replay and divergent grant-generation fault
  tests.
- [x] T023 [AC008, N001-N004, D001-D006] Add CLI/MCP parity, deterministic digest,
  no-network, bounded payload and installed-wheel contract tests.
- [x] T024 [AC001-AC010, D001-D009] Regenerate fixtures/templates and run focused,
  public-contract, MCP, installed-wheel and full suites on every supported
  Python version.
