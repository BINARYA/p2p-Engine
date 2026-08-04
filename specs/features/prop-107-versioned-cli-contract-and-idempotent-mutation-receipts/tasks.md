# Tasks - Versioned CLI Contract And Idempotent Mutation Receipts

## Phase 0 - Inventory And Contract

- [x] T001: Bind accepted `PROP-107` to requirements, design and tasks. Covers
  R001-R034.
- [x] T002: Inventory every CLI command supporting JSON, its current top-level
  shape, exits and known WaveKit/agent consumer. Covers R001-R011, AC001-AC002.
- [x] T003: Implement envelope/error/exit primitives and golden contract
  fixtures. Covers R001-R007, R009-R010.
- [x] T004: Normalize Typer/Click parser and argument failures in JSON mode.
  Covers R008-R011, AC002.
- [x] T005: Convert all inventoried JSON commands and add an inventory guard
  test. Covers R001-R011, AC001.

## Phase 1 - Version Discovery

- [x] T006: Implement `p2p version` from shared package/runtime constants.
  Covers R012-R015, AC003.
- [x] T007: Add source-tree and installed-wheel text/JSON version tests outside
  a project root. Covers R012-R015, AC003.

## Phase 2 - Receipt Core

- [x] T008: Add typed receipt/status models, key validation, canonical request
  fingerprinting and hashed receipt paths. Covers R016-R018, R021, R023.
- [x] T009: Implement receipt lookup, corruption/recovery classification and
  postcondition verification. Covers R024-R031, AC004-AC007.
- [x] T010: Add `p2p mutation status --idempotency-key` with redacted text/JSON
  output. Covers R029-R031, AC007.

## Phase 3 - Idempotent Vertical Applies

- [x] T011: Require idempotency keys on install/adopt/migrate apply and bind
  exact semantic request fingerprints. Covers R016-R020.
- [x] T012: Commit success receipts in the same atomic candidate as install,
  adopt and migrate mutations. Covers R021-R023, R027-R028, AC006.
- [x] T013: Implement exact replay, divergent-input conflict and postcondition-
  drift behavior. Covers R024-R028, AC004-AC007.
- [x] T014: Add response-loss, repeated replay, changed actor/token/mapping,
  injected write failure and recovery tests for all three operations. Covers
  R016-R028, AC004-AC007.

## Phase 4 - Integration And Verification

- [ ] T015: Publish WaveKit golden fixtures and retry/status integration
  guidance using operation UUIDs. Covers R032-R034.
- [ ] T016: Update CLI reference and release notes for the breaking envelope
  and required idempotency keys. Covers R001-R034.
- [ ] T017: Run focused transaction/service tests, public CLI/MCP tests, wheel
  smoke and full suite; record evidence. Covers AC001-AC008.
- [ ] T018: Add an implementation note linking completed coverage and any
  explicitly deferred historical-mutation retrofit to `PROP-107`.
