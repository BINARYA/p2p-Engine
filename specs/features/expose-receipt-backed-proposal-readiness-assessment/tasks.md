# Tasks - Expose Receipt-Backed Proposal Readiness Assessment

## Phase 0 - Boundary And Contract

- [x] T001: Audit P2P Engine `0.4.10` proposal readiness calculation, CLI,
  proposal-detail read model, receipt support, workspace transactions and MCP
  handler, and record the concrete gaps in requirements/design. Covers
  R001-R019, R040-R047.
- [x] T002: Fix the implementation boundary: one receipt-backed assessment
  mutation, proposal-detail freshness, shared MCP atomicity, and no new
  project-readiness mutation. Covers R020-R052, AC010-AC011.
- [x] T003: Add a concise implementation inventory mapping every requirement to
  the exact source/test/doc files that will change; completion is a reviewed
  inventory in this feature directory or the implementation note. Covers
  R048-R052.

## Phase 1 - Pure Assessment Planning

- [x] T004: Introduce a typed internal proposal-readiness assessment plan with
  final readiness payload, candidate bytes/path, profile identity, policy
  version, source preconditions and aggregate source fingerprint. Covers
  R007-R013, N006.
- [x] T005: Refactor evidence-aware readiness calculation so it can produce the
  final assessment without calling a writing `initialize()` or writing an
  intermediate readiness snapshot. Covers R001-R007, AC002.
- [x] T006: Define the explicit bounded source inventory and deterministic
  source-fingerprint algorithm, including absent optional files and the active
  readiness profile. Covers R008-R013, N004.
- [x] T007: Preserve and validate existing owner override fields in the final
  candidate while keeping `readiness.yml` outside its own evidence fingerprint.
  Covers R005, R012-R013, AC007.
- [x] T008: Make human/local assessment commit exactly one validated readiness
  candidate through `AtomicMutationWriter`, without adding a receipt
  requirement to text mode. Covers R006, R024-R025, R039, N001.

## Phase 2 - Freshness Read Model

- [x] T009: Add read-only readiness freshness calculation for `not_assessed`,
  `current` and `stale`, with assessed/current source fingerprints and policy
  comparison. Covers R014-R019.
- [x] T010: Extend `p2p-proposal-detail/v1` readiness data with freshness,
  assessment policy version and source fingerprint fields while preserving all
  existing readiness fields. Covers R014-R018, R049.
- [x] T011: Add service/read-contract tests proving no file changes occur while
  reading not-assessed, current, stale or invalid readiness state. Covers
  R014-R019, N003, AC008.
- [x] T012: Add table-driven tests that mutate each declared source independently
  and prove freshness becomes stale, while unrelated files do not affect the
  fingerprint. Covers R008-R019, AC006, AC008.

## Phase 3 - Receipt-Backed Assessment

- [x] T013: Register and strictly validate mutation receipt operation
  `proposal_readiness_assess` and operation id
  `proposal.readiness.assess`, including bounded readiness result fields and
  proposal-bound canonical changed paths. Covers R020-R028.
- [x] T014: Add sanitized public mutation-status serialization for readiness
  receipts without raw keys or source contents. Covers R027-R029, AC004.
- [x] T015: Implement the workspace operation-key assessment method with
  semantic request fingerprint, exact replay and divergent actor/proposal
  conflict behavior. Covers R020-R023, R026-R029.
- [x] T016: Commit readiness candidate and receipt in one
  `AtomicMutationWriter` call with every calculation dependency registered as a
  source precondition. Covers R024-R030, N001-N002.
- [x] T017: Normalize blocked, failed, source-changed, incomplete transaction,
  corrupt receipt and postcondition-drift outcomes to stable readiness
  assessment errors. Covers R025, R029-R030, R037.
- [x] T018: Add receipt tests for applied, exact replay, divergent key reuse,
  missing receipt, corrupt receipt, postcondition drift and exact retry after
  later evidence changed. Covers R020-R030, AC003-AC004.
- [x] T019: Add failure-injection tests before journaling, during readiness
  replacement, during receipt replacement and after replacements, proving
  complete rollback or explicit recovery. Covers R024-R030, N001-N002, AC005.
- [x] T020: Add a concurrency/source-drift test proving evidence changed between
  plan and lock-protected commit cannot publish a mixed-snapshot assessment.
  Covers R025, N001, AC006.

## Phase 4 - CLI JSON Contract

- [x] T021: Extend `p2p proposal readiness assess` with `--actor`,
  `--operation-key` and `--format`, requiring the operation key only in JSON
  mode. Covers R031-R039.
- [x] T022: Emit the typed `proposal_readiness_assess` plus `mutation` payload
  under operation `proposal.readiness.assess` and the existing `p2p-cli/v1`
  envelope. Covers R031-R036, AC001.
- [x] T023: Preserve the current human invocation and useful text output while
  routing it through the shared atomic assessment implementation. Covers
  R038-R039, AC009.
- [x] T024: Add CLI success, replay, missing key, malformed key, divergent key,
  missing proposal, invalid source, busy transaction and recovery-required
  tests with stable exits and error codes. Covers R031-R039, AC001-AC005.
- [x] T025: Add golden JSON contract fixtures from observed command output and
  assert complete field sets rather than hand-authored approximate payloads.
  Covers R032-R037, N004, N010.

## Phase 5 - MCP And Agent Parity

- [x] T026: Route `p2p_proposal_readiness_assess` through the shared atomic
  local assessment path and preserve its protocol-native governance metadata.
  Covers R040-R043, AC009.
- [x] T027: Review MCP catalog schema and descriptions; update them only where
  required to describe freshness and atomic assessment truthfully, without
  adding a CLI envelope. Covers R040-R043, R048.
- [x] T028: Add MCP parity tests comparing semantic readiness fields with CLI
  and proposal-detail results and proving no owner decision or override is
  performed. Covers R003-R005, R040-R043, AC009.
- [x] T029: Update generated agent capabilities/templates so standalone agents
  understand when to assess, how to inspect freshness, and why WaveKit workers
  use the keyed CLI path instead of MCP stdio. Covers R043, R048-R050, AC011.

## Phase 6 - Project Readiness Regression Boundary

- [x] T030: Add or refine regression tests proving `project snapshot`,
  `project progress` and `project readiness review` remain read-only and derive
  current vertical-based progress without a recalculation write. Covers
  R044-R046, AC010.
- [x] T031: Review wording around `p2p assess refresh` and ensure docs/tests do
  not conflate its operational assessment with proposal readiness or vertical
  project progress. Covers R044-R047, AC010-AC011.

## Phase 7 - Documentation And Release

- [x] T032: Update `docs/CLI-CONTRACT.md` with the keyed assessment command,
  receipt/status retry flow, proposal-detail freshness and project-readiness
  boundary. Covers R048-R050.
- [x] T033: Update `docs/CLI-GUIDE.md`, `docs/MCP.md`,
  `docs/development/cli-primitive-inventory.md`, `README.md` and `CHANGELOG.md`
  with implemented behavior and standalone examples. Covers R048-R050.
- [x] T034: Add an implementation note mapping requirements and acceptance
  criteria to source, tests, observed command output, docs and residual risks.
  Covers R048-R052, AC011-AC012.
- [x] T035: After implementation evidence exists, bump current release
  references from `0.4.10` to `0.4.11` without rewriting valid historical
  release records. Covers R051-R052.
- [x] T036: Update version-consistency and current-surface tests for `0.4.11`
  and verify package, MCP server, docs and release URLs agree. Covers R051-R052.

## Phase 8 - Verification And Handoff

- [x] T037: Run focused readiness, proposal read-contract, receipt, workspace
  transaction, CLI and MCP tests; completion is reviewed passing output.
  Covers AC001-AC011.
- [x] T038: Run `./scripts/test-public.sh` or the repository's equivalent
  public CLI/MCP contract suite; completion is reviewed passing output. Covers
  N010, AC001-AC012.
- [x] T039: Build the wheel and run installed-wheel smoke for assessment
  success, replay, mutation status and proposal-detail freshness. Covers N010,
  AC001-AC012.
- [x] T040: Run `./scripts/test-full.sh -q`; completion is reviewed passing
  output or an explicit residual-risk note. Covers AC012.
- [x] T041: Review all task checkboxes against implementation evidence and mark
  only genuinely completed work before release handoff. Covers AC012.
