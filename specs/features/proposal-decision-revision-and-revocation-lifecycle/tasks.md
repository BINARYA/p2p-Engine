# Tasks - Proposal Decision Revision And Revocation Lifecycle

## Task-State Rule

- Governed source: accepted `PROP-102`.
- Delivery Change Set: `CHANGE-070`.
- `[x]` means direct evidence already exists.
- `[ ]` means planned work and must not be treated as implementation evidence.
- A task is complete only when its code, focused test and stated review evidence
  exist.
- Implementation must follow
  `specs/skills/ENGINEERING_QUALITY_SKILL.md` and
  `specs/skills/TEST_QUALITY_SKILL.md`.
- Do not edit `.p2p` manually. Use supported P2P commands for Change Set,
  runtime, migration, registry, projection and publication state.
- Do not release, tag, publish Git state, update the repository runtime contract
  or migrate this repository as an implicit implementation step. Those actions
  have separate owner-confirmed gates.

## Stable Delivery Order

```text
P
-> S1
-> S2
-> S3
-> S4
-> S5
-> S6
-> S7
-> S8
-> S9
-> G
-> D
-> H
-> D2
-> M
-> A
-> F
```

- `P`: governed origin, baseline and traceability.
- `S1`: core ledger model, codec, fingerprints and projections.
- `S2`: lifecycle policy, authority view and schema-v2 legacy adapter.
- `S3`: workspace schema v3 and v2-to-v3 migration.
- `S4`: owner-governed preview/apply, retry, concurrency and repair.
- `S5`: impact capture and remediation next actions.
- `S6`: proposal, registry, Change, Work, spec, project and export consumers.
- `S7`: decision context, topology, retrieval and freshness binding.
- `S8`: CLI public contract and compatibility commands.
- `S9`: MCP parity, consent binding, diagnostics, docs and agent templates.
- `G`: engine implementation completion gate.
- `D`: reproducible runtime release/deployment gate.
- `H`: pre-migration owner-attestation hardening discovered by repository
  dry-run.
- `D2`: reproducible patch runtime release/deployment gate for hardening.
- `M`: this repository's owner-controlled v2-to-v3 migration.
- `A`: derived artifact alignment and baseline comparison.
- `F`: final validation, residual review and handoff.

No slice may start before the preceding exit gate unless the work is a
test-only fixture or independent documentation inventory.

## Requirement Coverage

| Slice | Requirements | Primary planned tests/evidence |
| --- | --- | --- |
| P | baseline, N001..020 | inventories, failing regressions, traceability matrix |
| S1 | R-F1-001..022 | ledger codec, fingerprint, projection unit tests |
| S2 | R-F2-001..021, R-F5-004..005 | transition matrix, authority and legacy adapter tests |
| S3 | R-F5-001..019, R-F5-023 | schema, migration, recovery and operation-gate tests |
| S4 | R-F3-001..023, R-F5-020..022 | preview/apply, atomicity, retry, concurrency and repair tests |
| S5 | R-F4-001..014 | impact completeness, pagination and next-action tests |
| S6 | R-F2-022, R-F6-001..019 | consumer convergence and projection-corruption regressions |
| S7 | R-F7-001..012 | source, extraction, topology, retrieval, freshness and scale tests |
| S8 | R-F8-001..006, R-F8-011, R-F8-016..017 | CLI text/JSON and compatibility tests |
| S9 | R-F8-007..015 | MCP consent/parity, validation, docs and skill drift tests |
| G | AC001..028 | focused, public, full, package and installed-runtime evidence |
| D | R-F9-001..004 | release artifact and runtime installation evidence |
| H | R-F5-024..031, AC031..034 | attestation parser, template, planner, apply and failure tests |
| D2 | D026, R-F9-001..004 | patch release and installed-runtime parity |
| M | R-F9-005..009 | repository dry-run, apply, recovery and authority curation |
| A | R-F9-010..014 | derived rebuild, publication and baseline comparison |
| F | AC029..030, residual state | final traceability and owner handoff |

## Implementation Rules

- Keep typed domain behavior out of `cli.py`, CLI renderers, MCP handlers,
  exporters and `P2PWorkspace`.
- Use a single ledger codec and a single lifecycle-authority service.
- Use strict YAML parsing and canonical serialization. Do not implement the
  ledger with regex or ad hoc string replacement.
- Reuse `MutationPreviewService`, `AtomicMutationWriter`,
  `PermissionsService`, `WorkspaceOperationCompatibilityService` and the
  registered migration framework.
- Keep `proposal.md` section replacement and full `decision.md` rendering
  deterministic and centralized.
- Do not create a persistent preview cache.
- Do not infer decision semantics from Git, mtime, process user or local
  timezone.
- Do not let presentation pagination alter impact completeness or token
  semantics.
- Do not mutate downstream Change, Work, spec, vertical, code or publication
  state during decision apply.
- Test domain policy at the lowest useful layer; use CLI/MCP tests only for
  their distinct public contracts.
- Every multi-target or migration test must assert exact bytes before and after
  failure.
- Keep public JSON changes additive except for the approved two-step decision
  write behavior.
- Preserve unrelated worktree changes and avoid broad refactors.

## Live Traceability Warning

The requirement -> design -> task -> test/evidence matrix must be updated at
every slice exit. Do not wait for `G` or `F`.

For each completed task:

1. record exact requirement IDs;
2. identify the design section and implementation symbol;
3. record focused test names and command;
4. record any compatibility or residual decision;
5. leave the task unchecked if evidence is partial.

Create `implementation-evidence.md` in this feature directory when
implementation begins. It is local stable documentation, not canonical P2P
state.

## P - Governed Origin, Baseline And Guardrails

- [x] P-T001: Verify `PROP-102` is accepted with decision-ready readiness and
  no failed gates. Evidence: `p2p proposal show/readiness show PROP-102`.
- [x] P-T002: Create `CHANGE-070`, set it to `planned`, run implementation-spec
  lifecycle preflight and generate the P2P-native software spec through
  supported commands.
- [x] P-T003: Inspect the current overwrite writer, lifecycle policy, direct
  decision readers, CLI/MCP write surfaces, permission model, mutation writer,
  workspace operation gate, migration handlers and relevant tests.
- [x] P-T004: Re-read accepted `PROP-102`, `CHANGE-070`, its generated software
  spec and all three local feature documents immediately before implementation;
  record any drift rather than silently choosing one source.
- [x] P-T005: Create `implementation-evidence.md` with package/runtime baseline,
  workspace schema baseline, source commit, Python versions and focused/full
  command catalog.
- [x] P-T006: Initialize a requirement -> design -> task -> planned-test matrix
  covering every R-F*, N*, E* and AC* identifier.
- [x] P-T007: Inventory all public decision commands, options, success/error
  text, JSON fields, MCP tool names/schemas, consent operations and docs before
  changing behavior.
- [x] P-T008: Inventory every direct `proposal.md` status and `decision.md`
  decision read in `src/p2p_engine`; classify it as proposal-body parsing,
  schema-v2 adapter use, projection display or authority bug.
- [x] P-T009: Inventory every write operation ID passed to the common workspace
  operation gate and identify the v3-only decision/repair/legacy-resolution
  additions and the old `proposal_decision_record` compatibility path.
- [x] P-T010: Capture current schemas and semantic outputs for proposal show,
  proposal list, full review, registries, Change creation, software-spec
  preflight, project refresh/progress/maturity/assessment, vertical evidence,
  context, next, freshness, export and publication.
- [x] P-T011: Add focused failing regressions proving an accepted decision can
  currently be overwritten as rejected and that normal reads lose prior
  acceptance history.
- [x] P-T012: Add a failing consumer regression where `proposal.md` and
  `decision.md` diverge and different consumers select different authority.
- [x] P-T013: Add fixture builders for schema-v2 and schema-v3 workspaces,
  aligned/divergent legacy decisions, all lifecycle events, multi-event chains,
  dependency graphs and 100-proposal scale.
- [x] P-T014: Define focused test commands for S1-S9 and run the current
  relevant suites to isolate pre-existing failures from feature regressions.
- [x] P-T015: Run `p2p validate`, workspace schema status, registry status and
  derived freshness status read-only on this repository and record the
  pre-implementation baseline without refreshing artifacts.
- [x] P-T016: Confirm exact public behavior change for legacy decision commands:
  preview without token, apply only with matching token and confirmation, no
  one-step fallback.
- [x] P-T017: Confirm the diagnostic allocation `P2P360..P2P389` is still
  collision-free before adding constants/tests.
- [x] P-T018: Move `CHANGE-070` to `implementation_ready` through the P2P CLI
  only after this spec, baseline and unresolved-design review are complete.
- [x] P-T019: P exit gate. No unresolved question may remain about ledger path,
  schema v3, event identity, owner/MCP authority, migration ownership, repair
  policy or compatibility-command behavior.

## S1 - Ledger Model, Codec, Fingerprints And Projections

- [x] S1-T001: Add core enums/dataclasses for event types, effective states,
  authority resolution, lineage, authority evidence, impact binding, migration
  provenance, events, ledgers, intervals, lifecycle views, requests, previews
  and results. Covers R-F1-001..005.
- [x] S1-T002: Freeze ledger contract version, event schema version, proposal
  semantics policy version, decision semantics policy version and event
  integrity policy version as named constants. Covers R-F1-002..003, N003.
- [x] S1-T003: Implement strict duplicate-key-detecting YAML load support using
  established structured parsing helpers and repository-relative diagnostics.
  Covers R-F1-015..016, E030.
- [x] S1-T004: Implement an empty schema-v3 ledger renderer/parser and prove
  canonical byte round-trip for an undecided proposal. Covers R-F1-001..002,
  R-F1-018, AC001.
- [x] S1-T005: Implement closed root/event/authority/predecessor/lineage/impact/
  readiness/mutation/migration field validation with future-contract failure.
  Enforce documented UTF-8 byte/count/control-character limits before hashing
  or writing. Covers R-F1-003..006, R-F1-015..016, R-F1-022.
- [x] S1-T006: Implement canonical proposal semantic extraction that excludes
  status/projection fields, rejects duplicate semantic sections and normalizes
  accepted conditions explicitly. Covers R-F1-009..010, N005.
- [x] S1-T007: Add proposal fingerprint tests for LF/CRLF, list formatting,
  YAML/Markdown ordering where relevant, absolute-root differences, clocks,
  status-only changes and material proposal changes.
- [x] S1-T008: Implement decision semantic fingerprints for accepted and
  conditionally accepted authority, typed structured conditions with stable
  IDs/duplicate validation, and affected-decision references for later events.
  Covers R-F1-003, R-F1-009, R-F2-010..012, R-F2-021.
- [x] S1-T009: Implement operation-key normalization, full request fingerprint,
  event-ID derivation, event hash calculation and full-digest prefix collision
  detection. Covers R-F1-007..008, R-F3-011..012.
- [x] S1-T010: Implement ordered predecessor/head chain validation and indexes
  by event ID, operation key and preview token in one parse, including
  non-decreasing canonical event dates. Covers R-F1-006, R-F1-008, R-F1-021,
  E005..007.
- [x] S1-T011: Add table tests for missing head, wrong final head, predecessor
  ID/hash mismatch, reordered events, duplicate IDs/keys, altered prior event
  unsupported event schema, boundary-size values and oversize/control-character
  rejection. Covers R-F1-022, AC002.
- [x] S1-T012: Implement typed lineage serialization/validation primitives for
  replacement, split and merge shapes without workspace discovery. Covers
  R-F1-004, R-F2-013..015.
- [x] S1-T013: Implement deterministic `proposal.md` status projection that
  changes only the Status section and preserves all other bytes. Covers
  R-F1-011, R-F3-009.
- [x] S1-T014: Implement deterministic full `decision.md` projection for every
  effective state, including `reinstated` event type with restored active
  status. Covers R-F1-011..013, R-F2-011.
- [x] S1-T015: Implement cross-validation of ledger, proposal projection and
  decision projection plus current proposal-to-event semantic binding with
  explicit missing/invalid/divergent results. Covers R-F1-013..014,
  R-F1-019..020, E004, E008.
- [x] S1-T016: Add projection golden tests for undecided, all terminal states,
  accepted-with-changes, revocation, replacement and reinstatement.
- [x] S1-T017: Add proposal artifact catalog/source ownership metadata so
  `decision-events.yml` is canonical and `decision.md` is a projection, while
  retaining schema-v2 catalog compatibility. Covers R-F1-017.
- [x] S1-T018: Run focused ledger, fingerprint, codec, artifact-catalog and
  projection tests; record symbols and test names in the live matrix.
- [x] S1-T019: S1 exit gate. Verify canonical round trips, chain tamper
  detection, deterministic fingerprints and projection equality before adding
  workspace-aware lifecycle rules.

## S2 - Lifecycle Authority, Transition Policy And Legacy Reads

- [x] S2-T001: Define the complete pure transition matrix and event-specific
  required-field policy in one versioned module. Covers R-F2-002..008,
  R-F2-020..021.
- [x] S2-T002: Add an exhaustive parameterized matrix test for every effective
  state/event cell, including exact retry distinction. Covers AC003.
- [x] S2-T003: Implement lifecycle reduction from a validated event chain to
  current effective state, head type, active/committed flags, ever-active,
  current decision fingerprint, proposal binding status, lineage and
  diagnostics. Covers R-F2-001, R-F2-016..019.
- [x] S2-T004: Derive authority intervals for initial acceptance, revocation,
  replacement and reinstatement; retain unknown-legacy precision explicitly.
  Covers R-F2-016, R-F7-005.
- [x] S2-T005: Implement reinstatement validation against explicit revocation
  and prior-active event references and exact decision/proposal fingerprints.
  Covers R-F2-010..012, E018..020.
- [x] S2-T006: Implement workspace-aware lineage validation over one captured
  proposal identity/lifecycle map, including self, duplicate, missing, terminal
  and reciprocal-evidence failures. Covers R-F2-013..015, E011, E021..022.
- [x] S2-T007: Define reconsideration diagnostics/next command for rejected and
  withdrawn proposals without creating a proposal automatically. Covers
  R-F2-008..009, AC005.
- [x] S2-T008: Implement `ProposalLifecycleAuthorityService` with schema-aware
  selection, one captured proposal snapshot and no projection-authority
  fallback in schema v3. Covers R-F2-001, R-F1-014, R-F5-004.
- [x] S2-T009: Implement the schema-v2 legacy adapter for aligned, pending,
  missing, malformed, divergent and unsupported values. Covers R-F5-004,
  R-F5-007..011.
- [x] S2-T010: Prove the legacy adapter never reads Git, mtime, process user or
  unrelated project metadata and emits explicit source provenance. Covers
  R-F5-011, N016.
- [x] S2-T011: Preserve the existing pure lifecycle helper only as a
  captured-token compatibility API; deprecate direct workspace use and add a
  source audit test preventing new service consumers. Covers R-F6-001.
- [x] S2-T012: Converge `decision_context_authority.py` lifecycle vocabulary
  with the new policy contracts without yet switching source extraction.
  Covers R-F2-002, R-F7-004.
- [x] S2-T013: Add lifecycle tests for never-active, previously-active,
  conditional authority, revoked, replaced, reinstated, deferred and unknown
  legacy states, including empty/duplicate/reordered structured acceptance
  conditions, migration of usable legacy qualifier text and current/diverged/
  unavailable proposal bindings. Covers R-F1-019..020, R-F2-021, AC004..006.
- [x] S2-T014: Add request-scoped lifecycle-map builder with one proposal
  discovery pass, at most one read/parse per source and stable proposal-ID
  ordering. Covers N008.
- [x] S2-T015: Add 100-proposal lifecycle-map structural tests and filesystem
  enumeration metamorphic tests.
- [x] S2-T016: Run focused lifecycle, legacy adapter, permissions vocabulary and
  authority tests; update traceability.
- [x] S2-T017: S2 exit gate. A consumer can receive one authoritative lifecycle
  view for v2 or v3 without parsing projections independently.

## S3 - Workspace Schema V3 And V2-To-V3 Migration

- [x] S3-T001: Set target workspace schema to 3 and update schema policy/layout
  constants, status serialization and fresh initialization fixtures. Covers
  R-F5-001, R-F5-023.
- [x] S3-T002: Add adjacent `workspace-v2-to-v3` transition metadata and
  registry validation while preserving v0-to-v1 and v1-to-v2 paths. Covers
  R-F5-001..003.
- [x] S3-T003: Register `WorkspaceV2ToV3ProposalDecisionLedgerHandler` with
  exact managed prefixes, validators and source-version requirements. Covers
  R-F5-006, R-F5-015..016.
- [x] S3-T004: Extend layout requirements so schema v3 requires
  `decision-events.yml` for every proposal and schema v2 remains upgradeable.
  Covers R-F5-004, R-F5-019, R-F5-023.
- [x] S3-T005: Update `ProposalDocumentService` fresh proposal creation to
  materialize the empty ledger only when the workspace contract is v3, while
  retaining v2 compatibility fixtures. Covers R-F1-001, R-F1-018.
- [x] S3-T006: Add operation requirements for all decision preview-independent
  writes, apply, legacy resolution and repairs; require v3 for event mutations
  and keep unrelated v1/v2-safe writes available. Covers R-F5-005,
  R-F3-016..017.
- [x] S3-T007: Implement deterministic migration capture for every valid
  proposal directory with duplicate-ID, unreadable-file and unsafe-path
  blockers. Covers R-F5-006, E027.
- [x] S3-T008: Implement aligned decided-proposal candidate rendering with one
  migrated event and complete legacy provenance. Covers R-F5-007.
- [x] S3-T009: Implement draft/pending migration to an empty resolved ledger.
  Covers R-F5-008.
- [x] S3-T010: Implement loss-aware unknown-legacy evidence for missing,
  malformed, unsupported and divergent sources with bounded raw values and full
  digests. Covers R-F5-009..013, E001..003.
- [x] S3-T011: Render matching `proposal.md` and `decision.md` candidates from
  every migration ledger after preserving original values. Covers R-F5-006,
  R-F5-015.
- [x] S3-T012: Add candidate validation that parses every ledger, re-derives
  lifecycle, verifies both projections and validates source provenance before
  the schema candidate is accepted. Covers R-F5-016.
- [x] S3-T013: Ensure candidate operation order is ledger then proposal/decision
  projections per proposal in stable ID order, with workspace schema/history
  last. Covers R-F5-006.
- [x] S3-T014: Add v2-to-v3 dry-run tests proving zero writes, stable plan
  fingerprint, stable operation order and exact target ownership. Covers
  R-F5-014..016, AC015.
- [x] S3-T015: Add migration fixture tests for all recognized outcomes, pending,
  missing fields, malformed values, divergence, unknown files and 100
  proposals. Covers AC016.
- [x] S3-T016: Add failure injection before/after staging, validation, journal
  and every proposal/schema replacement; assert exact v2 rollback or
  recovery-required state. Covers R-F5-017.
- [x] S3-T017: Add recovery status, rollback and resume tests for an interrupted
  v2-to-v3 transaction with a changed external source. Covers R-F5-014,
  R-F5-017.
- [x] S3-T018: Add idempotent post-migration plan/apply no-op tests. Covers
  R-F5-018.
- [x] S3-T019: Add composed v0-to-v3 and v1-to-v3 tests proving adjacent handler
  ownership and no question/decision evidence loss. Covers R-F5-002.
- [x] S3-T020: Add old-runtime/new-v3 and new-runtime/v2 compatibility tests,
  including one unrelated safe write and one blocked decision write. Covers
  R-F5-003..005, E026..027.
- [x] S3-T021: Extend global validation, schema status, doctor and migration
  diagnostics for missing/invalid ledger, unknown legacy and projection drift.
  Covers R-F5-019.
- [x] S3-T022: Update initialization, migration, operation-gate and version
  consistency tests to share the same current-version constants. Covers
  R-F5-023.
- [x] S3-T023: Run focused schema, compatibility, migration, transaction,
  initialization and validation tests; update traceability.
- [x] S3-T024: S3 exit gate. Fresh v3 and migrated v3 workspaces have one
  validated ledger and matching projections per proposal, while v2 remains
  readable and event-write blocked.

## S4 - Governed Mutation, Retry, Concurrency And Repair

- [x] S4-T001: Refactor `ProposalDecisionService` constructor around ledger,
  lifecycle, permission, impact, preview and atomic-writer collaborators;
  retain thin workspace facade delegation. Covers R-F3-001, N001..002.
- [x] S4-T002: Add typed `status()` and bounded `history()` service methods with
  no writes and stable cursor binding to proposal/head/policy. Covers R-F8-001,
  R-F1-006.
- [x] S4-T003: Implement one normalized `ProposalDecisionRequest` builder for
  all event types, explicit date, operation key, reason, structured conditions,
  references, lineage and optional acceptance readiness override. Covers
  R-F3-001, R-F3-006..007, R-F3-023.
- [x] S4-T004: Resolve CLI owner authority and separate MCP executor from
  owner-approval evidence using `PermissionsService`; bind permission bytes and
  policy version. Covers R-F3-004..005, R-F3-019.
- [x] S4-T005: Implement read-only preview capture for proposal, ledger,
  projections, readiness, permissions, lineage and impact sources in one
  request snapshot. Render readiness override only for explicit acceptance,
  block activating events on semantic divergence and require explicit drift
  acknowledgement for active-to-inactive events. Covers R-F3-002..003,
  R-F3-022..023.
- [x] S4-T006: Render candidate event, appended ledger and both projections from
  the snapshot and validate the candidate lifecycle before token generation.
  Covers R-F3-003, R-F3-009.
- [x] S4-T007: Build preview token context with operation, actor/owner,
  permissions, source head, proposal/decision/impact fingerprints, date,
  lineage and request fingerprint. Covers R-F3-006.
- [x] S4-T008: Implement apply exact-retry lookup before fresh candidate
  evaluation and return `already_applied` only for complete semantic equality.
  Expose the committed result binding needed by adapters without authorizing a
  new write. Covers R-F3-011, R-F3-015, R-F3-021, E017.
- [x] S4-T009: Implement operation-key and preview-token replay mismatch
  detection with `P2P366` and byte-invariant failure tests. Covers R-F3-012.
- [x] S4-T010: Rerun preview on apply, compare token, require confirmation and
  distinguish stale source from concurrent ledger head. Covers R-F3-007..008,
  R-F3-013.
- [x] S4-T011: Commit ledger, proposal and decision candidates in one
  `AtomicMutationWriter` call, adding readiness only for explicit acceptance
  override, with all target/non-target source preconditions and under-lock
  candidate validation. Covers R-F3-008..010, R-F3-023.
- [x] S4-T012: Add failure injection after every normal and readiness-override
  replacement and during rollback; assert all-old, all-new or durable
  recovery-required state. Covers R-F3-010, R-F3-023, AC009.
- [x] S4-T013: Add separate-process same-request concurrency test proving one
  event and one `already_applied` result. Covers R-F3-014, AC010.
- [x] S4-T014: Add separate-process conflicting-request concurrency test proving
  one event and one `P2P367` result. Covers R-F3-014.
- [x] S4-T015: Add clock/date metamorphic retry tests proving response-loss
  retry succeeds with the explicit preview date and operation key. Covers
  R-F3-015, R-F3-020.
- [x] S4-T016: Remove all direct write behavior from the old
  `ProposalDecisionService.record()` path; retain only a compatibility adapter
  that requires preview/apply semantics. Covers R-F3-017.
- [x] S4-T017: Prove managed branch accept/reject commands and MCP branch tools
  do not append ledger events. Covers R-F3-018.
- [x] S4-T018: Implement projection-repair preview/apply from a valid ledger and
  test status-only, decision-only and both-projection drift. Covers R-F5-020,
  AC018.
- [x] S4-T019: Implement explicit ledger-repair candidate parsing and maximal
  valid-prefix preservation checks. Covers R-F5-021..022.
- [x] S4-T020: Add ledger-repair tests for exact restoration, valid suffix,
  removed event, reordered event, changed prefix, broken continuity and future
  schema. Covers E025.
- [x] S4-T021: Implement unknown-legacy owner-resolution preview/apply as a
  first current event preserving legacy evidence and unknown historical
  interval. Covers R-F5-012..013.
- [x] S4-T022: Add owner-resolution tests for active, conditional, deferred,
  withdrawn and rejected current decisions; normal apply remains blocked before
  resolution. Covers E024.
- [x] S4-T023: Add tree/byte snapshot tests proving status, history and all
  preview/failed-apply paths are side-effect free. Covers N004, N007.
- [x] S4-T024: Run focused decision service, permissions, preview, transaction,
  concurrency, repair and recovery tests; update traceability.
- [x] S4-T025: S4 exit gate. No authority-changing write exists outside the
  shared service, and exact retry/concurrency/repair invariants pass.

## S5 - Revocation Impact And Remediation

- [x] S5-T001: Add immutable impact snapshot/item/page/completeness models and
  versioned dependency-kind/status/severity/remediation vocabularies. Covers
  R-F4-001..003.
- [x] S5-T002: Inventory exact canonical and derived inputs for Change Sets,
  Work, specs, vertical evidence, project projections, decision context,
  relations/conflicts, freshness and publication. Covers R-F4-002.
- [x] S5-T003: Implement one-pass source capture and indexes by proposal,
  Change, Work, spec, vertical section, relation and freshness node. Covers
  R-F4-002..004.
- [x] S5-T004: Implement stable impact identity, complete tuple ordering and
  source fingerprint independent of display pagination. Covers R-F4-004..005.
- [x] S5-T005: Implement direct and transitive dependency traversal with cycle
  protection, no nested workspace rediscovery and access counters. Covers
  R-F4-002..004.
- [x] S5-T006: Classify active, completed, terminal, historical, generated,
  curated and owner-controlled dependencies with explicit relationship and
  authority effect. Covers R-F4-003.
- [x] S5-T007: Implement bounded page/cursor output with totals, omitted counts,
  kind/status counts and completeness diagnostics. Covers R-F4-005.
- [x] S5-T008: Block authority-changing preview when malformed sources can hide
  dependencies; keep known optional derived absence advisory. Covers R-F4-006,
  E013.
- [x] S5-T009: Integrate complete impact binding into revoke, supersede, split,
  merge and reinstate preview/apply. Covers R-F4-001, R-F4-006..007.
- [x] S5-T010: Add fixtures covering active/completed Changes, Work, current/
  modified specs, vertical mappings, context relations, conflicts, stale
  projections and publication stages. Covers AC012, E023.
- [x] S5-T011: Prove a dependency hidden after the visible page still changes
  the token and stales apply when modified. Covers E012.
- [x] S5-T012: Add byte snapshots of every dependent path before and after
  revocation; only ledger and projections may change. Covers R-F4-008,
  AC013.
- [x] S5-T013: Implement generated remediation candidates in
  `NextActionService` with deterministic IDs, explicit ranks, current head
  binding and established dedupe precedence. Covers R-F4-009..012.
- [x] S5-T014: Add reinstatement remediation review actions without deleting
  prior log/evidence or restoring technical state. Covers R-F4-013.
- [x] S5-T015: Add next-action tests for multiple affected dependencies,
  unrelated proposals, curated precedence, stable order, caller limits and
  repeated requests. Covers R-F4-009..013.
- [x] S5-T016: Add read-only side-effect and 100-proposal impact performance
  tests with structural access thresholds. Covers R-F4-014, AC025.
- [x] S5-T017: Run focused impact, dependency service, next actions,
  freshness/publication status and scale tests; update traceability.
- [x] S5-T018: S5 exit gate. Impact is complete before token generation,
  rendering is bounded and decision apply never mutates dependent lifecycles.

## S6 - Consumer Convergence

- [x] S6-T001: Add a shared request-scoped lifecycle map provider to
  `P2PWorkspace` service construction without placing policy in the facade.
  Covers R-F6-001, R-F6-018.
- [x] S6-T002: Update proposal show/list/status/full review models and
  serialization with additive effective state, head, history, authority,
  ever-active, binding and fingerprint fields. Gate semantic proposal updates:
  allow undecided/deferred or normalization-equivalent changes and require a
  linked proposal otherwise. Covers R-F2-022, R-F6-002.
- [x] S6-T003: Update proposal artifact review and exporter ownership so the
  ledger is canonical and projection history is not duplicated. Covers
  R-F6-017.
- [x] S6-T004: Refactor global proposal validation to consume ledger/lifecycle
  diagnostics and projection comparison rather than independent status
  equality. Covers R-F5-019, R-F6-001.
- [x] S6-T005: Update registry record building and registry source definitions
  to retain stable IDs/fields and add head, history, authority, lineage and
  fingerprint metadata. Covers R-F6-003..004.
- [x] S6-T006: Add registry tests for active, conditional, deferred, rejected,
  revoked, superseded, reinstated and unknown-legacy proposals and prove history
  is not copied unbounded into registries.
- [x] S6-T007: Update Change Set creation to require active accepted/
  conditional authority and bind ledger path, head event and decision
  fingerprint in new included-decision records. Covers R-F6-005.
- [x] S6-T008: Add backward-compatible Change reader support for old
  `included-decisions.yml` entries and current-source resolution without mass
  rewrite. Covers R-F6-005..006.
- [x] S6-T009: Add Change status/impact diagnostics for revoked, replaced and
  unresolved sources without changing Change lifecycle status. Covers
  R-F6-006, R-F6-008.
- [x] S6-T010: Update Work planning preconditions to block new work on inactive
  or unresolved governing sources while preserving existing Work records.
  Covers R-F6-006..008.
- [x] S6-T011: Update software-spec lifecycle/source collection to bind event
  head/fingerprint, classify inactive source and avoid overwriting an affected
  existing spec. Covers R-F6-007, R-F6-012.
- [x] S6-T012: Add tests for planned/in-progress/completed Change, new/existing
  Work and current/stale/modified specs after source revocation and
  reinstatement.
- [x] S6-T013: Refactor accepted proposal projection building in project state
  and context packets to consume active lifecycle views. Covers R-F6-009.
- [x] S6-T014: Refactor project progress, maturity and assessment to use current
  active authority and expose historical counts separately where useful.
  Covers R-F6-009.
- [x] S6-T015: Refactor vertical evidence activation to use lifecycle authority
  while preserving historical mappings and definition completeness. Covers
  R-F6-010..011.
- [x] S6-T016: Update relations/conflicts to validate event lineage and
  quarantine incompatible active assertions. Covers R-F6-016.
- [x] S6-T017: Update derived freshness source policies and software-spec
  fingerprints with ledger head and lifecycle policy versions. Covers
  R-F6-012..013.
- [x] S6-T018: Update visible export and publication inputs to distinguish
  active, previously-active, never-active and unresolved decisions. Covers
  R-F6-014..015.
- [x] S6-T019: Add one projection-corruption regression per consumer family;
  valid ledger authority must control or the consumer must report drift. Add
  accepted-body semantic divergence and prove claim consumers block without
  treating the event as revoked. Covers R-F1-019..020, R-F6-001, R-F6-019,
  AC019.
- [x] S6-T020: Add revocation/reinstatement integration fixture proving active
  views change, historical rationale remains, dependencies remain and
  fingerprints/freshness update.
- [x] S6-T021: Run focused proposal, registry, Change, Work, spec, project,
  vertical, assessment, maturity, progress, freshness, export and publication
  tests; update traceability.
- [x] S6-T022: Run `rg` inventory again and classify every remaining direct
  status/decision read as body parsing, v2 adapter, projection rendering or
  defect; fix every authority defect.
- [x] S6-T023: S6 exit gate. All non-context consumers use one lifecycle view
  and no dependent lifecycle is automatically rewritten.

## S7 - Decision Context, Topology, Retrieval And Semantic Freshness

- [x] S7-T001: Add ledger source kind/classification and schema-aware source
  catalog selection: ledger canonical in v3, `decision.md` legacy canonical in
  v2 and derived projection in v3. Covers R-F7-001..002.
- [x] S7-T002: Implement strict structured ledger source capture with one
  read/hash/parse per request and structured fragment/evidence paths. Covers
  R-F7-003.
- [x] S7-T003: Extend known lifecycle vocabulary and extractor policy versions
  for withdrawn, revoked, reinstated and unknown legacy. Covers R-F7-004,
  R-F7-011.
- [x] S7-T004: Extract one stable decision event node/record set per event with
  current/historical authority and canonical dates. Covers R-F7-003..005.
- [x] S7-T005: Extract event predecessor, affected-decision, supersession, split,
  merge and reinstatement relations without duplicating projection evidence.
  Covers R-F7-005..006.
- [x] S7-T006: Represent authority intervals and event-head binding in context
  records/packets with additive serialization. Covers R-F7-005, R-F7-008.
- [x] S7-T007: Update topology normalization and incompatible-lineage
  diagnostics for ledger-backed assertions. Covers R-F7-006.
- [x] S7-T008: Update retrieval authority rank so equal active evidence outranks
  historical evidence, while historical rationale remains eligible and
  labelled. Covers R-F7-007.
- [x] S7-T009: Add retrieval golden tests for active accepted, conditional,
  revoked, rejected, withdrawn, superseded, reinstated and unknown legacy
  evidence. Covers AC021.
- [x] S7-T010: Include head event, interval, lineage and decision fingerprint in
  material retrieval/context hits and future-memory binding fields. Covers
  R-F7-008, R-F7-010.
- [x] S7-T011: Update source/semantic fingerprints so revoke/reinstate changes
  context fingerprint and invalidates a head-bound stale summary. Covers
  R-F7-009.
- [x] S7-T012: Prove `decision.md` projection edits do not create duplicate
  authority records in v3 and instead produce only projection diagnostics.
  Covers E029.
- [x] S7-T013: Add schema-v2 source catalog regressions preserving current
  behavior until migration. Covers R-F7-002.
- [x] S7-T014: Add 100-proposal multi-event scale fixture, source access
  counters, enumeration-order metamorphic tests and bounded context payload
  assertions. Covers R-F7-012, AC025.
- [x] S7-T015: Update decision-context, topology, retrieval and freshness policy
  version tests and any materialized manifest/source contract.
- [x] S7-T016: Run focused source, extraction, authority, topology, retrieval,
  context packet, freshness and performance tests; update traceability.
- [x] S7-T017: S7 exit gate. Current and historical event authority is
  explainable, head-bound, deterministic and not double-counted.

## S8 - CLI Public Contract

- [x] S8-T001: Refactor decision CLI registration into thin helpers for request
  parsing, text rendering, JSON serialization and common error exit behavior.
  Covers R-F8-001..006.
- [x] S8-T002: Add `decision status` text/JSON with lifecycle, head, history,
  authority, interval, lineage and projection diagnostics. Covers R-F8-001,
  R-F8-011.
- [x] S8-T003: Add bounded `decision history` text/JSON with limit/cursor and
  stable truncation metadata. Covers R-F8-001.
- [x] S8-T004: Add generic `decision preview` for every event type with
  explicit reason, repeated/file-backed structured conditions, actor, date,
  operation key, references and typed lineage.
  Covers R-F8-002..003.
- [x] S8-T005: Add generic `decision apply` requiring the normalized preview
  inputs, token and `--confirm`; map every blocked result to nonzero exit.
  Covers R-F8-002, R-F8-006.
- [x] S8-T006: Add read-only bounded impact command/detail rendering with total
  counts, omitted count, blockers, warnings and apply ingredients. Covers
  R-F8-003.
- [x] S8-T007: Add projection-repair preview/apply commands. Covers R-F8-004.
- [x] S8-T008: Add ledger-repair preview/apply with an explicit source path and
  reviewed candidate diagnostics. Covers R-F8-004.
- [x] S8-T009: Add legacy-resolution preview/apply with owner, date, current
  outcome and preserved-evidence summary. Covers R-F8-004.
- [x] S8-T010: Route `proposal accept`, `proposal reject`, `proposal defer` and
  `decision record` through shared preview/apply; remove immediate overwrite
  behavior and preserve `--override-readiness` only as an atomic accepted
  candidate. Covers R-F3-023, R-F8-005, R-F8-017.
- [x] S8-T011: Define compatibility command output/exit semantics for
  `preview_required`, matching apply, stale token and v2 schema-required cases.
  Covers R-F8-005..006.
- [x] S8-T012: Add CLI tests proving command names remain, existing semantic
  options parse, no-token invocation writes nothing and token+confirm appends
  exactly one event. Prove readiness override preview, stale and failed apply
  leave readiness bytes unchanged. Covers R-F8-017, AC023.
- [x] S8-T013: Add text/JSON parity tests for status, history, preview, impact,
  apply and repair stable fields. Covers AC022.
- [x] S8-T014: Add invalid transition, authority, lineage, reinstatement, stale,
  replay, recovery, confirmation and future-contract exit-code tests.
- [x] S8-T015: Add JSON automation fixture proving preview output supplies the
  exact operation key/date/token needed for cross-day apply retry.
- [x] S8-T016: Update CLI help snapshots and command guide source strings
  without embedding domain policy in help code.
- [x] S8-T017: Run focused decision CLI, proposal compatibility, validation and
  command-help tests; update traceability.
- [x] S8-T018: S8 exit gate. Every CLI decision write is visibly two-phase,
  owner-controlled and semantically identical to the service API.

## S9 - MCP, Consent, Diagnostics, Documentation And Agent Guidance

- [x] S9-T001: Define MCP schemas for decision status, history, preview, apply,
  projection repair, ledger repair and legacy resolution with bounded read
  arguments, optional accepted-decision readiness override and explicit
  mutation fields. Covers R-F8-007..010, R-F8-017.
- [x] S9-T002: Implement MCP read handlers as thin serialization over the same
  service results used by CLI JSON. Covers R-F8-007.
- [x] S9-T003: Add consent operation/target convention
  `proposal_decision_apply` / `PROP-XXX@preview-token` and validate current
  owner approval. Covers R-F8-008.
- [x] S9-T004: Keep MCP executor and owner authority identities separate in the
  event and result; test owner executor, agent executor and non-owner approval.
  Covers R-F3-005, R-F3-019.
- [x] S9-T005: Implement MCP apply and repair handlers with consume-on-success
  and used-with-error behavior on possible head change. Recognize a consumed
  receipt only for an exact committed-result binding. Covers R-F3-021,
  R-F8-008.
- [x] S9-T006: Route or deprecate existing MCP accept/reject/defer tools without
  permitting old unbound consent to write v3 events. Covers R-F8-009.
- [x] S9-T007: Add MCP catalog/registry tests for names, schemas, permission
  classes and absence of unregistered write tools.
- [x] S9-T008: Add MCP parity tests comparing normalized status/history/
  preview/apply/impact/repair payloads with CLI JSON. Covers AC022.
- [x] S9-T009: Add consent tests for wrong actor, wrong owner, wrong proposal,
  wrong token, expired/revoked receipt, exact consumed-receipt retry,
  consumed-result mismatch, replay and permission change. Covers R-F3-021,
  E028, AC007.
- [x] S9-T010: Define constants and structured mappings for P2P360..P2P389;
  integrate global validation, doctor, context and next recovery text. Covers
  R-F8-011..013.
- [x] S9-T011: Add diagnostics tests for ledger missing/invalid, chain,
  projection, transition, owner, stale, replay, concurrent head, reinstatement,
  lineage, impact, repair, consent and future contract. Covers AC024.
- [x] S9-T012: Update `docs/CLI-GUIDE.md`, `docs/MCP.md`, `docs/GLOSSARY.md`,
  development guidelines, migration docs and release notes with lifecycle and
  compatibility behavior. Covers R-F8-014.
- [x] S9-T013: Update source agent templates and P2P engine/project skills with
  rejection vs revocation, two-phase writes, migration v3 and branch-operation
  separation. Covers R-F8-014..015.
- [x] S9-T014: Refresh generated agent instructions only through
  `p2p agent ...` lifecycle commands when required and test template/generated
  drift. Covers R-F8-015.
- [x] S9-T015: Add docs/root/MCP hygiene tests preventing direct `.p2p` edit
  advice, one-step decision write guidance or `deprecated` as decision outcome.
- [x] S9-T016: Run focused MCP, consent, validation, doctor, docs and agent
  integration tests; update traceability.
- [x] S9-T017: S9 exit gate. CLI and MCP use one domain service, owner authority
  is explicit and all public guidance matches schema-v3 behavior.

## G - Engine Completion Gate

- [x] G-T001: Run all focused S1-S9 tests together and resolve shared-fixture,
  ordering and policy-version interactions.
- [x] G-T002: Run the complete transition matrix, migration matrix, failure
  injection and separate-process concurrency suites in one gate.
- [x] G-T003: Run the 100-proposal multi-event lifecycle, impact and
  decision-context performance fixtures and record structural counters and
  payload sizes.
- [x] G-T004: Run source audits proving no schema-v3 authority consumer parses
  projection status independently and no decision writer bypasses the shared
  service.
- [x] G-T005: Run byte-invariance tests for every read, preview, failed apply,
  migration plan and blocked repair path.
- [x] G-T006: Run `./scripts/test-public.sh -q`; completion is clean public CLI,
  MCP, docs and package-contract evidence.
- [x] G-T007: Run `./scripts/test-full.sh -q`; completion is a clean full suite
  or explicit isolation of failures proven unrelated to this feature.
- [x] G-T008: Run version consistency, import checks, static/type/lint checks
  defined by repository tooling and Python supported-version tests.
- [x] G-T009: Build wheel and sdist in a clean directory, verify release
  contents and run isolated installed-artifact smoke tests for v2 reads, v3
  fresh init, decision preview/apply and v2-to-v3 dry-run.
- [x] G-T010: Validate fresh v3, readable v2, migrated v3, unknown-legacy,
  projection-drift, recovery-required and ahead-of-runtime fixtures with
  `p2p validate` equivalents.
- [x] G-T011: Review public JSON additions, intentional command behavior change,
  diagnostic stability, consent classes and runtime/schema support matrix.
- [x] G-T012: Complete every requirement -> design -> task -> test/evidence row;
  no aggregate slice row may hide an untested requirement.
- [x] G-T013: Re-run `p2p spec lifecycle --intent implementation_spec --change
  CHANGE-070` and refresh the P2P-native software spec only if governed inputs
  or generator contracts changed through supported primitives.
- [x] G-T014: Set `CHANGE-070` to `in_progress` or later only according to actual
  implementation state through supported P2P commands; do not infer completion
  from local task checkboxes.
- [x] G-T015: G exit gate. Engine code is releasable and schema-v2 compatibility
  plus v3 migration are proven before any release or repository mutation.

## D - Runtime Release And Deployment

- [x] D-T001: Select the target `0.4.x` version and confirm package metadata,
  runtime support ranges, migration transition requirements, templates,
  changelog and docs agree. Covers R-F9-001.
- [x] D-T002: Run clean full/public/package tests from the exact candidate
  commit on the supported Python matrix. Covers R-F9-002..003.
- [x] D-T003: Inspect the complete candidate diff for unrelated files,
  generated-source drift and accidental `.p2p` manual edits.
- [x] D-T004: Ask the owner for explicit authorization before commit/tag/push or
  package publication; record exact version, commit and target.
- [x] D-T005: Create the release commit and tag only after authorization and
  only when G remains green.
- [x] D-T006: Build wheel/sdist from the tagged commit, verify hashes and run
  isolated installation smoke tests without source-tree import leakage.
  Covers R-F9-002.
- [x] D-T007: Publish the runtime artifact only after owner authorization, then
  verify the published artifact/version and installation command.
- [x] D-T008: Compare installed runtime behavior with source-checkout behavior
  for runtime status, schema status, v2 reads, migration plan and decision help.
- [x] D-T009: D exit gate. A reproducible installed v3-capable runtime exists;
  the repository workspace is still v2 and unchanged by this gate.

## H - Pre-Migration Owner Attestation Hardening

- [x] H-T001: Extend requirements, design, task order and live traceability for
  the owner-attestation contract, source binding, unsupported lineage cases,
  patch-release gate and repository dry-run evidence. Covers R-F5-024..031.
- [x] H-T002: Add a closed, versioned normalization contract for
  `proposal_decisions.authority_attestations`, including stable proposal and
  condition ordering, exact source-hash keys and bounded structured
  conditions. Covers R-F5-024..026, R-F5-030.
- [x] H-T003: Add a typed, read-only attestation-template result that exposes
  source-plan fingerprint, normalized owner input, included proposal IDs and
  explicit manual-review reasons. Covers R-F5-029.
- [x] H-T004: Generate templates only for aligned, authority-complete simple
  outcomes and a currently declared owner. Classify accepted-with-changes as
  requiring conditions and terminal lineage states as requiring historical
  review. Covers R-F5-025..026, R-F5-029..031.
- [x] H-T005: Consume attestations in the v2-to-v3 handler without changing
  target ownership, operation order, schema-last behavior or transaction
  boundaries. Covers R-F5-024, R-F5-028, R-F5-031.
- [x] H-T006: Validate exact legacy summary, owner role and source bytes before
  creating an event; emit `P2P390_MIGRATION_ATTESTATION_INVALID` and block apply
  on semantic mismatch. Covers R-F5-025, R-F5-030.
- [x] H-T007: Build attested events with current-owner authority and
  `workspace_migration_owner_attestation` channel while preserving original
  actor and values in migration provenance. Covers R-F5-027.
- [x] H-T008: Support explicit structured conditions for
  `accepted_with_changes`; prove `superseded` and other predecessor/lineage
  states remain unknown rather than becoming fabricated initial events. Covers
  R-F5-026..027.
- [x] H-T009: Add `p2p workspace migrate attestation-template` as a read-only
  text/JSON command and expose the typed service through `P2PWorkspace`.
  Covers R-F5-029.
- [x] H-T010: Add normalization and template unit tests for unknown fields,
  unsafe identities, duplicate IDs, malformed dates/hashes, deterministic
  ordering, unsupported states and no-write behavior.
- [x] H-T011: Add migration tests for exact attestation success, non-owner,
  source-summary/hash mismatch, accepted-with-changes conditions, unsupported
  lineage, fingerprint changes, omitted input and lock-time source staleness.
  Covers AC031..034.
- [x] H-T012: Add CLI tests and update workspace migration documentation with
  the generated-template review flow, authority semantics and patch-release
  prerequisite.
- [x] H-T013: Run formatting/static checks, focused migration/service/CLI
  suites, full public/full repository suites and `git diff --check`; update
  implementation evidence and the live traceability matrix.
- [x] H-T014: H exit gate. The source implementation is releasable, exact owner
  attestations preserve active simple legacy authority, and unsupported history
  remains explicit. Repository schema remains v2.

## D2 - Attestation Patch Runtime Release And Deployment

- [x] D2-T001: Select the next `0.4.x` patch version and align package metadata,
  changelog, runtime support and docs without weakening schema-v2 reads.
- [ ] D2-T002: Run clean Python 3.11 and local Python matrix tests, package
  verification and isolated installed-artifact smoke from the exact candidate
  commit.
- [x] D2-T003: Review the complete patch diff and confirm no migration,
  `.p2p` repair, derived rebuild or publication approval was included.
- [ ] D2-T004: Ask for explicit owner authorization before commit, tag, push or
  package publication; record exact version, commit and target.
- [ ] D2-T005: Publish and install the owner-authorized patch artifact, then
  prove source/installed parity for template, plan, fingerprint and apply help.
- [ ] D2-T006: D2 exit gate. The repository runtime contract accepts the
  installed patch and M may resume using that executable.

## M - Repository V2-To-V3 Migration

- [x] M-T001: Ask the owner to confirm repository runtime-contract update and
  v2-to-v3 migration as separate persistent operations.
- [x] M-T002: Through supported runtime preview/apply, update this project's
  runtime contract to the verified `0.4.x` version/range; do not edit the YAML
  manually. Covers R-F9-008.
- [x] M-T003: Verify the active installed executable, package location, runtime
  contract and source commit before any migration plan.
- [x] M-T004: Capture read-only baseline: runtime/schema status, validation,
  proposal lifecycle distribution, registries, project progress/maturity/
  assessment, Changes, Work, specs, freshness, export/publication and Git diff.
  Covers R-F9-005.
- [x] M-T005: Run `p2p workspace migrate plan --to 3 --format json` with no
  owner patch and archive the reviewed plan evidence outside canonical `.p2p`
  state in the feature implementation evidence. Covers R-F9-005..006.
- [x] M-T006: Verify plan target ownership, proposal count, ledger count,
  operation order, candidate validation, source hashes, unknown preservation,
  derived refresh advisories and schema-last commit. Covers R-F9-006.
- [x] M-T007: Enumerate every unknown-legacy/blocking proposal and request owner
  input only where safe authority cannot be established. Covers R-F9-007.
- [ ] M-T008: After D2, generate and review the owner-attestation template,
  complete structured accepted-with-changes input, re-plan with the supported
  patch and confirm fingerprint, candidate changes, residual manual-review
  cases and no unrelated target changes.
- [ ] M-T009: Ask for explicit owner confirmation of the exact applicable plan
  fingerprint and actor.
- [ ] M-T010: Apply the migration through `p2p workspace migrate apply`; do not
  run concurrent governed writes.
- [ ] M-T011: If apply is interrupted, stop normal work and use migration
  recovery status/rollback/resume according to the journal; record result
  before continuing.
- [ ] M-T012: Verify schema v3, migration history, one ledger per proposal,
  valid chains, matching projections and no unexplained authority divergence.
  Covers R-F9-009.
- [ ] M-T013: Resolve each remaining unknown-legacy proposal only through the
  owner legacy-resolution preview/apply primitive, one reviewed operation at a
  time. Covers R-F9-007, R-F9-009.
- [ ] M-T014: Re-run validation and lifecycle distribution after every curation
  batch; stop on any new active-authority count not explained by owner input.
- [ ] M-T015: Run a second v3 migration plan and prove it is a no-op.
- [ ] M-T016: M exit gate. Canonical workspace state is schema v3, ledger-valid,
  projection-aligned and owner-curated where required; derived artifacts may
  still be stale.

## A - Derived Artifact Alignment

- [ ] A-T001: Run registry status/refresh through the owning command and compare
  proposal/decision/change/artifact counts with baseline. Covers R-F9-010..012.
- [ ] A-T002: Refresh project projections through the owning command; verify
  active decisions, historical states, decision map bindings and ownership
  manifest. Covers R-F9-010..012.
- [ ] A-T003: Rebuild/read decision context and compare source/evidence/node/
  relation counts, diagnostics, semantic fingerprint and active/historical
  authority distribution.
- [ ] A-T004: Refresh assessment and maturity where owned; recompute progress
  and verify definition completeness remains distinct from active proposal
  evidence.
- [ ] A-T005: Inspect every software spec status. Refresh only specs whose
  lifecycle permits deterministic refresh; leave modified/imported/inactive-
  source specs explicit for review.
- [ ] A-T006: Refresh managed next actions and verify deterministic revocation/
  migration/remediation actions, curated precedence and no obsolete schema-v2
  instructions.
- [ ] A-T007: Refresh visible project export through its owner command and
  verify active/historical/unresolved decision wording and traceability.
- [ ] A-T008: Prepare/refresh publication packet only when its prerequisites are
  current; do not silently curate or approve publication.
- [ ] A-T009: Run curator import, publication validation and render only through
  their separate supported stages if requested; keep owner publication review
  unchanged. Covers R-F9-011, R-F9-013.
- [ ] A-T010: Run full derived freshness status and ensure every stale/partial
  node has an owning command, explicit blocker or owner/agent review class.
- [ ] A-T011: Compare pre/post proposal state counts, event counts,
  ever-active/current-active counts, Change/Work/spec impacts, vertical
  evidence, progress axes, registry/context/projection fingerprints and
  publication status. Covers R-F9-012.
- [ ] A-T012: Record every residual manual repository action with target,
  evidence, supported primitive and required owner authority; no direct `.p2p`
  repair. Covers R-F9-014.
- [ ] A-T013: Run focused and full tests against the migrated repository state
  plus `p2p validate`.
- [ ] A-T014: A exit gate. Canonical and derived state are aligned or every
  remaining non-current artifact is explicitly lifecycle-controlled.

## F - Final Validation And Handoff

- [ ] F-T001: Review `PROP-102`, `CHANGE-070`, generated software spec and local
  implementation specs against the final code and migrated workspace.
- [ ] F-T002: Complete the full requirement -> design -> task -> test/evidence
  matrix with direct evidence for AC001..AC030 and no unchecked implemented
  work.
- [ ] F-T003: Re-run source audits for direct decision writes, direct projection
  authority reads, unknown operation IDs, unbound MCP consent and mtime/Git
  inference.
- [ ] F-T004: Re-run all focused S1-S9 tests, public suite, full suite, package
  verification, installed smoke tests and repository validation.
- [ ] F-T005: Confirm exact retry, concurrency, migration recovery, projection
  repair, ledger repair rejection and unknown-legacy curation evidence remains
  passing after all integration changes.
- [ ] F-T006: Confirm no decision apply changed dependent Change, Work, spec,
  vertical, code, Git or publication lifecycle state automatically.
- [ ] F-T007: Confirm current exports and retrieval never present revoked,
  rejected, withdrawn or replaced decisions as active constraints.
- [ ] F-T008: Confirm future memory-compaction inputs expose proposal, head,
  interval, lineage and source fingerprint without implementing compaction.
- [ ] F-T009: Review Git diff and generated artifacts, preserving unrelated
  owner changes and excluding temporary build/test output.
- [ ] F-T010: Through P2P CLI, set `CHANGE-070` lifecycle status according to
  actual implementation/review completion; owner-controlled completion remains
  with the owner.
- [ ] F-T011: Produce a concise final handoff with implemented behavior, public
  compatibility change, migration outcome, test evidence, residual risks and
  publication state.
- [ ] F-T012: F exit gate. AC029 and AC030 are directly proven: the repository
  migration was owner-controlled, all ledgers/projections are explained and no
  publication approval was inferred.

## Planned Focused Commands

Adjust filenames only if implementation follows an established test split with
equivalent coverage.

```bash
.venv/bin/pytest -q \
  tests/test_proposal_decision_ledger.py \
  tests/test_proposal_decision_service.py \
  tests/test_proposal_lifecycle_authority_service.py

.venv/bin/pytest -q \
  tests/test_workspace_v3_migration.py \
  tests/test_workspace_migration_service.py \
  tests/test_workspace_schema_service.py \
  tests/test_workspace_operation_compatibility.py \
  tests/test_workspace_transactions.py

.venv/bin/pytest -q \
  tests/test_proposal_decision_impact.py \
  tests/test_next_actions_service.py \
  tests/test_change_set_lifecycle_service.py \
  tests/test_work_planning_service.py \
  tests/test_software_spec_lifecycle_service.py \
  tests/test_software_spec_service.py

.venv/bin/pytest -q \
  tests/test_registry_record_builder_service.py \
  tests/test_registry_service.py \
  tests/test_project_state_service.py \
  tests/test_project_progress_service.py \
  tests/test_project_maturity_service.py \
  tests/test_project_assessment.py \
  tests/test_project_verticals.py \
  tests/test_derived_freshness_service.py

.venv/bin/pytest -q \
  tests/test_decision_context_sources.py \
  tests/test_decision_context_service.py \
  tests/test_decision_context_topology.py \
  tests/test_decision_context_retrieval_service.py \
  tests/test_context_packet_service.py

.venv/bin/pytest -q \
  tests/test_cli_proposal_decisions.py \
  tests/test_cli.py \
  tests/test_mcp_proposal_decisions.py \
  tests/test_mcp.py \
  tests/test_mcp_registry.py \
  tests/test_docs_root_mcp_hygiene.py

./scripts/test-public.sh -q
./scripts/test-full.sh -q
```

## Residual Review Questions

These are implementation review checkpoints, not unresolved scope choices:

- Does the existing consent artifact support token-bound targets without a
  contract-version bump, or should its target metadata become structured and
  versioned?
- Can existing migration candidate validation efficiently validate all proposal
  ledgers in one overlay, or is a bounded validator index required?
- Does `AtomicMutationWriter` recovery expose enough decision-specific context
  in generic journals, or is additive operation metadata needed?
- Which existing proposal/registry JSON dataclasses can gain additive fields
  without breaking positional construction in tests or downstream code?
- Should explicit remediation software-spec work use a new lifecycle intent, or
  can current implementation-spec preflight expose a reviewed override without
  weakening normal inactive-source blockers?

Each question must be resolved in the owning slice before code depending on it
is merged. None permits bypassing owner authority, ledger integrity or
two-phase apply.
