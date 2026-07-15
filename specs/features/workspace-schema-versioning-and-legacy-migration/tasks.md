# Tasks - Workspace Schema Versioning And Legacy Migration

All tasks are initially unchecked. A task is complete only when its stated code,
test, measured behavior, owner input or repository migration evidence exists.
Planning text alone is not implementation evidence.

## Identifier Stability

This task plan preserves the original work identifiers.

- `F1`-`F9`: reusable P2P Engine capabilities.
- `M1`-`M5`: controlled migration work for this repository.
- Task ids use `<work-id>-T<nnn>`.

Do not replace these identifiers with a new plain numeric phase list.

## Delivery Order And Exit Gates

| Work | Depends on | Exit gate |
| --- | --- | --- |
| Preparation | none | baseline, contracts and focused commands recorded |
| F1 | Preparation | layout/alignment and transition-runtime states work for all fixtures |
| F2 | F1 | deterministic forward-only no-write plan and complete finding classification |
| F3 | F2 | locked candidate-overlay apply, durability, rollback, recovery and idempotence pass |
| F6 | F3 | parser defects removed and atomic impact/conflict correction primitives exist |
| F4 | F6 | vertical migration is coherent and definition writes are previewable |
| F5 | F6 | domain/permissions/metadata migration is explicit, previewed and safe |
| F7 | F6 | bounded suggestion and atomic coverage/artifact-state import exist |
| F8 | F4, F5, F7 | two-axis progress contract passes |
| F9 | F4, F5, F7 | full-node freshness, lifecycle policy and owned-output reconciliation pass |
| M1 | F8, F9 and full suite | owner-reviewed repository dry-run exists |
| M2 | M1 | project definition is valid and owner-controlled gaps are explicit |
| M3 | M1 and F6 | remaining relation diagnostics are curated through supported writes |
| M4 | M1 and F7 | approved first-batch vertical mappings exist |
| M5 | M2, M3, M4 | every derived node rebuilt/assessed and compared with baseline |

F4, F5 and F7 may proceed in parallel after F6. F8 and F9 may proceed in
parallel after F4/F5/F7. M2, M3 and M4 proceed in small independently verified
batches after M1.

## Requirement Coverage

| Requirement group | Implemented/verified by |
| --- | --- |
| F1-R001-F1-R011 | F1-T001-F1-T014 |
| F2-R001-F2-R012 | F2-T001-F2-T018 |
| F3-R001-F3-R024 | F3-T001-F3-T032 |
| F4-R001-F4-R011 | F4-T001-F4-T015 |
| F5-R001-F5-R009 | F5-T001-F5-T013 |
| F6-R001-F6-R013 | F6-T001-F6-T017 |
| F7-R001-F7-R012 | F7-T001-F7-T017 |
| F8-R001-F8-R010 | F8-T001-F8-T015 |
| F9-R001-F9-R012 | F9-T001-F9-T018 |
| M1-R001-M1-R005 | M1-T001-M1-T015 |
| M2-R001-M2-R005 | M2-T001-M2-T015 |
| M3-R001-M3-R005 | M3-T001-M3-T014 |
| M4-R001-M4-R005 | M4-T001-M4-T011 |
| M5-R001-M5-R007 | M5-T001-M5-T016 |
| N001-N021, E001-E026 | preparation, focused fixture tasks and every slice exit gate |
| AC001-AC024 | G-T001-G-T010 and M5-T001-M5-T016 |

## Implementation Rules

- Keep domain logic in cohesive services behind `P2PWorkspace`.
- Keep CLI and MCP modules limited to transport, options and presentation.
- Use structured readers and typed payloads for all YAML/Markdown state.
- Prove read-only operations perform no writes.
- Never edit `.p2p` manually for repository migration tasks.
- Never infer owner vertical, identity, metadata or semantic relation choices.
- Never mark a historical artifact migrated only because its filename exists.
- Run focused tests at every slice exit; run the full suite before M1 and M5.
- Keep repository dogfooding evidence separate from generic engine tests.
- Record durable implementation and migration evidence only in
  `specs/features/workspace-schema-versioning-and-legacy-migration/implementation.md`.
- Treat preview/apply as one contract: actor, confirmation, source hashes and
  stale-preview behavior must be explicit for every semantic write primitive.
- Treat `layout_current` and semantic alignment as separate result dimensions.

## Preparation

- [x] P-T001: Re-read this feature, current runtime-contract migration specs,
  vertical hardening specs, decision-context implementation and repository
  audit before coding. Completion is the initial section of `implementation.md`
  naming reused services, contracts and known direct-write boundaries.
- [x] P-T002: Record the current public compatibility matrix for runtime status,
  validation, vertical context, definition, permissions, assessment, maturity,
  project refresh, registry refresh, doctor, project status, compact context,
  next actions, publication status and package/runtime release version.
- [x] P-T003: Create fixture factories for fresh current, minimal legacy,
  vertical-less software, active-without-lock, missing-permissions,
  malformed/ahead schema, inspect-but-not-apply runtime, downgrade request,
  concurrent apply, stale lock and interrupted-transaction workspaces.
- [x] P-T004: Create a historical decision/relation fixture corpus reproducing
  free-form Outcome, pending decisions, collection-valued rejected proposals,
  supported aliases, ambiguous aliases and invalid free-text targets.
- [x] P-T005: Record focused test commands per `F*` group and the full validation
  command. Completion is a stable command/evidence table in `implementation.md`
  updated with actual module paths and pass counts as tests are added.
- [x] P-T006: Add a reusable filesystem mutation assertion for status, plan,
  semantic previews, suggestion, progress, freshness, doctor, compact context
  and generated next-action calls.
- [x] P-T007: Freeze initial public constants: workspace contract version,
  current workspace layout version, layout/alignment states, migration result
  names, transition capability fields,
  lock states, semantic/physical hash fields, finding/action classes and
  diagnostic namespace.
- [x] P-T008: Preparation exit review. Confirm no implementation task requires
  direct `.p2p` editing or an owner decision hidden as an automatic default.

## F1 - Workspace Schema Versioning

- [x] F1-T001: Add core enums and typed contracts for workspace schema state,
  compatibility status, applied migration metadata and schema validation
  diagnostics, with separate layout/alignment dimensions and transition runtime
  support. Covers F1-R001-F1-R011.
- [x] F1-T002: Add deterministic serializers/parsers for
  `.p2p/project/workspace-schema.yml`; test empty, valid, malformed, unsupported
  contract version and unknown fields, plus contiguous registered history,
  duplicate/unknown migration ids and terminal-version consistency.
- [x] F1-T003: Implement a read-only `WorkspaceSchemaService.status()` that
  distinguishes `legacy_undeclared`, current, invalid, unsupported,
  ahead-of-runtime and incomplete migration states, and can report
  `layout_status=current` with alignment advisories without claiming semantic
  alignment.
- [x] F1-T004: Define current-layout requirements as versioned code data rather
  than one unconditional required-path list. Include canonical, optional,
  compatibility and derived classifications conditional on domain, selected
  vertical, enabled capabilities and schema version.
- [x] F1-T005: Integrate schema-state findings additively into global validation
  without turning valid legacy undeclared workspaces into uninspectable errors.
- [x] F1-T006: Extend project initialization so fresh workspaces write current
  schema state after required bootstrap artifacts are successfully created;
  inject failures proving no current marker is written for partial bootstrap.
- [x] F1-T007: Add `P2PWorkspace` facade delegation with no domain logic.
- [x] F1-T008: Add `p2p workspace schema status` text and JSON output with stable
  exit behavior.
- [x] F1-T009: Add CLI/service tests proving schema status does not change
  runtime status and performs no writes.
- [x] F1-T010: Add read-only MCP schema status only after CLI result shape is
  stable; test exact JSON parity.
- [x] F1-T011: Run focused schema, initialization, validation, CLI and MCP tests.
- [x] F1-T013: Add additive workspace-schema summary fields to doctor, project
  status and compact context, and generate a highest-priority migration or
  recovery next action without changing existing required output fields.
- [x] F1-T014: Add a versioned schema/runtime support matrix used by status and
  validation; test runtimes that can inspect/plan but cannot apply a transition.
- [x] F1-T012: F1 exit gate. Confirm fresh, current, legacy, invalid and ahead
  fixtures are distinguishable, layout and alignment are not conflated, global
  visibility is additive and existing runtime tests remain unchanged.

## F2 - Compatibility Analyzer And Dry-Run Plan

- [x] F2-T001: Add typed compatibility snapshot, finding, owner-input,
  operation, migration plan and plan-fingerprint contracts, including requested
  direction, transition runtime support and semantic/physical hashes. Covers
  F2-R001-F2-R012.
- [x] F2-T002: Implement one-pass workspace artifact inventory using normalized
  root-relative paths and captured source bytes/hashes.
- [x] F2-T003: Add versioned artifact classification for required, optional,
  legacy, canonical, derived, transient and unknown paths.
- [x] F2-T004: Integrate existing runtime, vertical, lock, definition, domain,
  permission, governance, proposal artifact, decision-context and freshness
  inspectors without duplicating their parsers.
- [x] F2-T005: Implement finding classification and stable recovery metadata for
  compatible, degraded, migration-required, owner-input, repository-curation,
  engine-prerequisite, unsupported and invalid states; represent current layout
  with unresolved curation as degraded rather than fully aligned.
- [x] F2-T006: Implement migration path planning against the registry introduced
  for F3, initially with pure fake transitions declaring inspect/plan/apply
  runtime capabilities in tests.
- [x] F2-T007: Implement ordered plan operations with before hashes, candidate
  intent, semantic candidate hashes, dependencies, write class, canonicality,
  validator, rollback description and expected physical-hash timing.
- [x] F2-T008: Implement normalized owner-input patch parsing and validation;
  reject unknown input fields and unsafe path/provenance values.
- [x] F2-T009: Implement deterministic plan fingerprinting and prove independence
  from timestamp, absolute root and enumeration order; prove a different apply
  date does not change semantic plan identity.
- [x] F2-T010: Add `p2p workspace migrate plan` with target-version, input-patch,
  text and JSON options; reject lower target versions with a stable no-write
  unsupported-downgrade result.
- [x] F2-T011: Add read-only MCP migration plan after CLI/service stabilization;
  do not add apply.
- [x] F2-T012: Test unknown durable artifacts are preserved and reported rather
  than removed or copied into candidate state.
- [x] F2-T013: Test a plan containing owner-input and repository-curation
  operations remains useful but non-applicable until blockers are resolved.
- [x] F2-T014: Prove planning creates no transaction directory, migration state,
  generated export or canonical write.
- [x] F2-T015: Run focused analyzer, CLI, validation and MCP tests.
- [x] F2-T017: Add forward-only path-resolution tests for current target, lower
  target, missing intermediate transition and inspect-but-not-apply runtime.
- [x] F2-T018: Add plan/result serialization tests proving semantic candidate
  hashes remain stable while final physical hashes and audit fields are reported
  only by apply results.
- [x] F2-T016: F2 exit gate. Snapshot the representative legacy JSON plan and
  confirm repeated/reversed-order planning is byte-equivalent, downgrade is
  rejected and transition runtime prerequisites are actionable.

## F3 - Transactional Migration Engine

- [x] F3-T001: Add migration transition protocol/ABC and registry with id,
  source/target versions, forward direction, inspect/plan/apply runtime support,
  dependencies, planner, renderer and validators.
- [x] F3-T002: Validate registry uniqueness, adjacency, acyclic paths and complete
  source-to-current migration routes at startup/test time; reject reverse edges,
  impossible runtime ranges and unknown capability names.
- [x] F3-T003: Add typed apply, staged-validation, rollback, interrupted and
  recovery result contracts with deterministic serialization.
- [x] F3-T004: Implement apply preflight for actor authority, explicit confirm,
  target version, resupplied owner inputs, plan fingerprint, current source
  hashes, target ownership and existing transaction detection; recompute the
  plan before lock acquisition and repeat source/target checks under the lock.
- [x] F3-T005: Implement safe same-filesystem transaction-directory creation and
  reject symlink/path escapes outside declared migration roots; reserve a
  private mode-`0700` root excluded from all ordinary discovery paths.
- [x] F3-T006: Implement journal creation containing plan fingerprint, target
  order, before hashes, original presence markers and transaction state; redact
  owner inputs/secrets and durably sync journal plus parent directory.
- [x] F3-T007: Snapshot original bytes and file metadata required for restoration
  before rendering candidates; preserve supported mode bits and reject rather
  than dereference migration-owned symlink targets.
- [x] F3-T008: Implement overlay rendering where each migration writes only its
  declared candidate targets.
- [x] F3-T009: Add artifact-owner validators and whole-overlay validation before
  replacement through a candidate workspace reader that routes migration-owned
  paths to staged bytes and records read provenance for tests.
- [x] F3-T010: Implement deterministic non-schema replacement order using atomic
  file helpers with file and containing-directory sync where supported; report
  explicitly when the platform cannot provide a durability guarantee and verify
  each target preimage immediately before replacement.
- [x] F3-T011: Commit workspace schema state/history last and verify the final
  registered version; render one apply-time audit timestamp and report semantic
  plan hashes separately from final physical hashes.
- [x] F3-T012: Implement reverse-order rollback for created, updated and removed
  targets.
- [x] F3-T013: Add injected failure tests before staging, during candidate
  validation and at every replacement position; assert exact original bytes
  and supported metadata after successful rollback, and refuse to overwrite a
  target externally changed after the transaction wrote it.
- [x] F3-T014: Implement interrupted transaction discovery and block unrelated
  new applies; expose the state to global validation and doctor without letting
  transaction scratch appear as an unknown durable artifact.
- [x] F3-T015: Implement recovery status and explicit rollback.
- [x] F3-T016: Implement resume only when journal state, candidate files and
  current hashes satisfy exact preconditions; otherwise require rollback.
- [x] F3-T017: Add CLI migrate apply and recovery status/rollback/resume with
  text/JSON output and stable exit codes; apply requires target version and the
  owner-input patch again in addition to the reviewed fingerprint.
- [x] F3-T018: Prove an already applied plan returns an idempotent no-op and does
  not append duplicate migration history or leave a lock/transaction directory.
- [x] F3-T019: Prove apply and rollback do not invoke raw Git or require network
  access.
- [x] F3-T020: Add tests for dirty/non-Git workspaces while preserving the plan's
  advisory checkpoint recommendation.
- [x] F3-T021: Run focused transaction, validation, CLI and facade tests.
- [x] F3-T023: Implement a process-safe exclusive migration lock with owner pid,
  transaction id and acquisition metadata; distinguish active, stale and
  recovery-owned locks without automatically stealing them.
- [x] F3-T024: Add a reusable durable transaction filesystem helper covering
  private scratch creation, atomic replacement, directory sync, cleanup and
  platform capability reporting.
- [x] F3-T025: Implement `CandidateWorkspaceView` and adapt global validation to
  accept an explicit candidate root/view; add a guard test that fails whenever a
  migration-owned validator reads the corresponding live target.
- [x] F3-T026: Add additive recovery/migration summaries to doctor, project
  status, compact context and next actions; interrupted recovery must outrank an
  ordinary schema-upgrade recommendation.
- [x] F3-T027: Run two-process concurrency tests, stale-lock tests, different-date
  plan/apply tests and crash simulations after journal, after each replace and
  before lock cleanup.
- [x] F3-T028: Add shared mutation-preview/result contracts and token generation
  over operation id, normalized targets, source preconditions, candidate
  semantics and policy version; prove tokens contain no source content/secrets.
- [x] F3-T029: Refactor runtime-contract update/adoption writes used by M1 to the
  multi-file transaction helper, or implement and test complete recovery from
  every explicit partial-failure position before authorizing repository use.
- [x] F3-T030: Add non-cooperating-writer tests that modify a not-yet-replaced
  target and an already-replaced target; prove commit detects the first and
  rollback preserves the second as explicit recovery-required state.
- [x] F3-T031: Integrate active migration lock checks into the common governed
  write preflight used by `P2PWorkspace`; test representative proposal, project,
  runtime, publication and next-action writes are blocked while read-only status,
  plan, context and doctor remain available.
- [x] F3-T032: Prove plan/preview is stateless: no durable cache is created,
  unchanged resupplied input applies, and omitted/changed input returns stale or
  invalid before lock acquisition and target writes.
- [x] F3-T022: F3 exit gate. No F6 or state migration work begins until complete
  rollback, exclusive locking, candidate-only validation, interrupted recovery,
  durability/cleanup, per-target concurrency protection, global write-preflight,
  stateless shared preview-token and runtime-contract alignment tests pass.

## F6 - Decision-Context Legacy Compatibility

- [x] F6-T001: Freeze a versioned lifecycle-state token table and relation alias
  policy with canonical, compatibility, ambiguous and invalid categories.
- [x] F6-T002: Refactor decision extraction to prefer recognized `Status`, use a
  recognized `Outcome` only as fallback state, and preserve free-form Outcome as
  decision content.
- [x] F6-T003: Add tests for PROP-001-style decisions, current decisions,
  accepted-with-changes, pending drafts and unknown legacy status.
- [x] F6-T004: Replace conflict winner/rejected scalar stringification with
  shared scalar-or-sequence normalization.
- [x] F6-T005: Add tests for one/many rejected proposals, empty lists, malformed
  values and deterministic supersession evidence.
- [x] F6-T006: Audit historical relation terms against canonical relation
  direction and add only unambiguous aliases.
- [x] F6-T007: Emit explicit ambiguous-relation diagnostics containing source,
  target, term, candidate meanings and required curation action.
- [x] F6-T008: Validate related-proposal target kinds and reject proposal
  relation entries whose target is unsupported free text.
- [x] F6-T009: Extend impact import validation so invalid relation vocabulary or
  target shape fails before replacing an existing artifact; parse and validate
  the complete supplied impact artifact set before any target write.
- [x] F6-T010: Add source-catalog/index regression proving compatibility aliases
  do not mutate files and ambiguous terms remain quarantined.
- [x] F6-T011: Re-run retrieval golden, determinism and scale tests after policy
  version change.
- [x] F6-T012: Add migration analyzer findings for source-specific ambiguous
  relations that require M3 curation.
- [x] F6-T013: Run focused decision source, extraction, topology, retrieval,
  artifact import and validation tests.
- [x] F6-T015: Add impact preview/apply service, facade and CLI contracts with
  per-target diff, source/candidate hashes, one preview token, actor authority
  and confirmation; apply reparses the resupplied artifact set and commits it
  atomically through the transaction helper. Preserve existing import syntax for
  compatible first-time workflows while routing committed corrections to apply.
- [x] F6-T016: Add conflict-memory show/preview-update/update-by-id service and
  CLI contracts validating proposal ids, type, winner/rejected consistency,
  reason and provenance; update reparses the supplied patch and rejects
  append-as-correction behavior.
- [x] F6-T017: Add stale-preview, partial-write injection and authority tests for
  impact and conflict correction, including one-invalid-file/no-target-change.
- [x] F6-T014: F6 exit gate. Compare diagnostics for the historical fixture and
  prove parser/list bugs are gone and M3 has previewable atomic correction
  primitives before any source rewrite task begins.

## F4 - Vertical Migration

- [x] F4-T001: Add a pure vertical migration candidate renderer that returns
  active state, lock, initial definition and rubric bytes without writing.
- [x] F4-T002: Detect domain/rubric evidence with missing active vertical and
  return candidate recommendations as owner inputs, not automatic selection.
- [x] F4-T003: Validate selected vertical resolution, version, checksum, profile
  and modules before candidate rendering.
- [x] F4-T004: Refactor existing select behavior to reuse the candidate renderer
  while preserving current CLI behavior for ordinary explicit selection; route
  handled writes through all-candidate validation and rollback-safe commit.
- [x] F4-T005: Add rubric matching by stable id and explicit semantic mapping for
  collisions.
- [x] F4-T006: Preserve unmatched legacy criteria as visible
  `legacy_unmapped` entries excluded from active baseline scoring.
- [x] F4-T007: Test enabled/disabled preservation, new default criteria,
  semantically conflicting ids and no silent deletion.
- [x] F4-T008: Register the vertical portion of the legacy-to-v1 migration and
  require owner vertical/profile/module inputs.
- [x] F4-T009: Stage and validate active state, lock, definition and rubrics as
  one transaction operation set.
- [x] F4-T010: Add failure injection proving no partial vertical state survives
  candidate or commit failure.
- [x] F4-T011: Extend validation so software-domain fallback is visible as a
  degraded/migration advisory without making read-only fallback mutate state.
- [x] F4-T012: Run focused vertical, maturity, validation, migration and CLI
  tests.
- [x] F4-T014: Add project-definition preview result/service/CLI containing
  normalized operations, semantic diff, source hash, resulting definition hash
  and stale-preview token, with no write or artifact-state side effect.
- [x] F4-T015: Add stale-preview-protected definition apply with actor and
  confirmation, resupplied patch and token recomputation while retaining
  backward-compatible parsing/delegation for the existing update command; test
  handled failures preserve original bytes.
- [x] F4-T013: F4 exit gate. Legacy vertical migration either produces four
  mutually coherent artifacts or leaves original state unchanged, and M2 has a
  supported preview/apply definition path.

## F5 - Legacy Domain, Permissions And Metadata Bootstrap

- [x] F5-T001: Define typed migration candidates for domain, permission and
  allowed project metadata fields.
- [x] F5-T002: Implement domain candidate rendering from valid manifest domain
  with provenance; require owner input when missing/unsupported.
- [x] F5-T003: Implement permission candidate rendering from explicit
  permissions or valid legacy governance roles plus owner identity input.
- [x] F5-T004: Add conflict detection for zero/multiple owners, unsupported roles
  and disagreement between legacy and explicit permissions.
- [x] F5-T005: Define a narrow project metadata patch for status, workflow phase
  and current goal while preserving id, remote and repository configuration.
- [x] F5-T006: Add service validation for metadata transitions and reject
  arbitrary top-level manifest replacement; preview only allowed field diffs and
  preserve runtime, project id, remote and repository configuration.
- [x] F5-T007: Register domain/permission/metadata operations in the
  legacy-to-v1 migration planner.
- [x] F5-T008: Ensure omitted optional metadata cleanup remains a visible owner
  input and prevents a false fully-aligned result when required by target schema.
- [x] F5-T009: Test migration does not rerun initialization, reinstall agents,
  rewrite runtime setup, or change remote settings.
- [x] F5-T010: Add facade/CLI input-patch plumbing without domain logic in CLI.
  Require actor, explicit confirmation and a matching stale-preview token for
  metadata apply, reparsing the resupplied patch while keeping plan input parsing
  read-only.
- [x] F5-T011: Run focused initialization, domain, permissions, governance,
  migration, validation and CLI tests.
- [x] F5-T013: Add metadata preview/apply authority, stale-token, allowed-field
  and audit tests, including an assertion that runtime/remote/repository bytes
  remain unchanged.
- [x] F5-T012: F5 exit gate. Current-shape domain and permissions can be staged
  safely from legacy evidence and explicit owner inputs, and metadata changes
  are previewed and bounded.

## F7 - Proposal Vertical-Coverage Primitive

- [x] F7-T001: Extend core vertical coverage model with backward-compatible
  optional provenance and authority fields.
- [x] F7-T002: Implement coverage show/status returning absent legacy, valid,
  invalid and vertical-mismatch states.
- [x] F7-T003: Implement a read-only suggestion service by replacing broad
  substring matches with section-specific phrase/token
  boundaries, source weighting, rare-term weighting and confidence thresholds;
  return evidence, confidence and reasons separately.
- [x] F7-T004: Prove suggestion does not create a file, artifact-state entry or
  topology relation.
- [x] F7-T005: Implement complete replacement import validation for proposal id,
  vertical id, section ids, relevance, rationale, source and provenance, and
  produce source/candidate hashes plus a deterministic semantic diff.
- [x] F7-T006: Implement atomic import through the proposal artifact service and
  preserve original bytes on invalid input or failed artifact-state update.
- [x] F7-T007: Add proposal artifact catalog/state integration with
  `required_when_applicable` semantics and commit coverage plus artifact-state
  provenance as one operation.
- [x] F7-T008: Add CLI vertical-coverage show, suggest and import commands with
  text/JSON parity, including no-write preview and import requiring actor,
  confirmation, resupplied payload and matching recomputed preview token.
- [x] F7-T009: Add read-only MCP show/suggest parity.
- [x] F7-T010: Add MCP import only if it can reuse the existing write-safe import
  boundary with exact target and payload validation; otherwise record explicit
  deferral without blocking CLI completion.
- [x] F7-T011: Add validation and decision-topology tests proving only imported
  declared coverage creates explicit section relations.
- [x] F7-T012: Test schema-v1 read compatibility and new provenance round trips.
- [x] F7-T013: Run focused vertical, proposal artifact, CLI, MCP, validation and
  decision-context tests.
- [x] F7-T015: Build a suggestion-quality fixture from this repository's known
  broad matches and prove generic terms cannot map most proposals to one section;
  low-confidence/no-evidence results return no candidate mapping.
- [x] F7-T016: Add coverage preview/apply stale-token, actor-authority and
  replacement-diff tests, including vertical change between preview and apply.
- [x] F7-T017: Add failure injection between coverage and artifact-state writes
  and prove both original artifacts are restored byte-for-byte.
- [x] F7-T014: F7 exit gate. One proposal can be suggested and imported without
  manual `.p2p` editing, heuristic authority promotion or partial provenance.

## F8 - Progress Model Convergence

- [x] F8-T001: Add typed project progress, axis, ratio, section evidence,
  blocker, assumption and question result models with policy version.
- [x] F8-T002: Implement definition completeness for explicit section status and
  required fields, including fieldless base sections.
- [x] F8-T003: Return `not_initialized` with no percentage when definition state
  is absent or invalid.
- [x] F8-T004: Implement evidence coverage from declared vertical mappings and
  proposal/decision lifecycle authority.
- [x] F8-T005: Report heuristic section suggestions separately and exclude them
  from declared coverage numerators.
- [x] F8-T006: Define denominator rules for required, optional and
  not-applicable sections and test every boundary.
- [x] F8-T007: Expose blockers, open questions and assumption states without
  converting them into hidden score penalties.
- [x] F8-T008: Add `ProjectProgressService` and thin facade delegation.
- [x] F8-T009: Add `p2p project progress` text and JSON output.
- [x] F8-T010: Add read-only MCP progress parity after CLI stabilization.
- [x] F8-T011: Add additive basis/freshness fields or warnings to legacy
  assessment and maturity output; preserve existing required fields.
- [x] F8-T012: Refine project readiness to consume definition and declared
  coverage while retaining heuristic evidence as a separate advisory field.
- [x] F8-T013: Add regression proving a keyword match in every proposal cannot
  produce authoritative 100-percent definition completeness.
- [x] F8-T014: Run focused progress, vertical, readiness, assessment, maturity,
  CLI and MCP tests.
- [x] F8-T015: F8 exit gate. Definition and evidence axes are independently
  reproducible from emitted counts and no overall opaque score is introduced.

## F9 - Derived-State Freshness

- [x] F9-T001: Inventory existing source fingerprints, generated timestamps,
  source counts and refresh services for every initial freshness node, explicitly
  including operational brief context/prompt/output, next actions/log,
  software-spec exports, visible exports and all publication stages.
- [x] F9-T002: Add typed freshness node, edge, status, reason and rebuild-action
  contracts.
- [x] F9-T003: Define and validate the dependency graph; reject cycles and
  unknown rebuild dependencies; encode deterministic, agent-curated,
  owner-reviewed and approval boundaries per node.
- [x] F9-T004: Implement current fingerprint/count collectors without rebuilding
  any artifact.
- [x] F9-T005: Detect fresh registries with stale rationalized project state,
  stale assessment/maturity, stale operational brief/next actions/spec exports
  and stale publication stages.
- [x] F9-T006: Produce a deterministic topologically ordered rebuild plan with
  exact existing commands where available, and name the missing primitive rather
  than inventing a command where no supported refresh exists.
- [x] F9-T007: Classify actions as deterministic, agent-curated, owner-review or
  approval and stop automatic orchestration before non-deterministic stages.
- [x] F9-T008: Add `p2p project freshness` text and JSON output.
- [x] F9-T009: Add read-only MCP freshness parity after CLI stabilization.
- [x] F9-T010: Optionally add deterministic refresh orchestration only after
  status/ordering tests pass; require confirmation, reuse existing services,
  reconcile owned outputs and stop before agent/owner nodes.
- [x] F9-T011: Ensure migration apply records downstream derived layers as stale
  by fingerprints/state, never by blindly touching output files or marking
  curated artifacts current.
- [x] F9-T012: Add mixed-success tests where one deterministic refresh fails and
  downstream stages remain stale with actionable reasons.
- [x] F9-T013: Run focused project state, registry, assessment, export,
  publication, CLI, MCP and migration tests.
- [x] F9-T015: Define the initial node catalog and ownership manifest for
  registries, project projections, decision context, assessment,
  maturity/progress, brief context/prompt/output, next actions/log, per-change
  software specs, visible exports and publication stages.
- [x] F9-T016: Replace exact `status == accepted` projection filtering with a
  shared versioned lifecycle-authority policy; test 93 `accepted` plus one
  `accepted_with_changes`, and define split/merged/superseded behavior.
- [x] F9-T017: Make project projection refresh reconcile its exact owned output
  set: create expected projections, remove stale owned projections and preserve
  unknown/manual directories; add failure and idempotence tests.
- [x] F9-T018: Add schema/freshness summaries to project status, compact context
  and next actions, with recovery then migration then derived refresh priority.
- [x] F9-T014: F9 exit gate. The known 82-versus-94 derived-state scenario is
  detected using the explicit committed-authority policy, receives the correct
  full-node rebuild order and leaves unknown outputs untouched in a fixture.

## Engine Completion Gate Before Repository Migration

- [x] G-T001: Run all focused F1-F9 suites together and resolve ordering or
  shared-contract regressions.
- [x] G-T002: Run the full repository test suite.
- [x] G-T003: Run performance tests on a deterministic 100-proposal migration
  fixture and record discovery/read/parse/write counters.
- [x] G-T004: Verify status, plan, suggestion, progress and freshness are
  mutation-free with cache/bytecode writes disabled where practical.
- [x] G-T005: Verify no MCP migration apply/recovery tool exists in v1.
- [x] G-T006: Review docs and command help against implemented public surfaces.
  Include CLI reference, MCP read contracts, migration/upgrade guide, generated
  agent instruction templates and recovery examples.
- [x] G-T007: Confirm all registered migration paths to current schema are
  complete, runtime/capability requirements are satisfiable and validation plus
  doctor recognize interrupted transactions and stale locks.
- [x] G-T009: Update package version, changelog/release notes and compatibility
  documentation together; test source/package/MCP version consistency and record
  the runtime-contract impact for existing exact-pinned workspaces.
- [x] G-T010: Verify generated agent instructions direct users to schema status,
  no-write plan and supported recovery commands and still forbid manual `.p2p`
  editing as a migration shortcut.
- [x] G-T008: Authorize M1 only after G-T001-G-T007, G-T009 and G-T010 pass;
  record the complete gate evidence in `implementation.md`.

## M1 - Repository Baseline And Owner-Reviewed Dry Run

- [x] M1-T001: Confirm the repository is on the intended branch and record Git
  cleanliness as advisory context; do not alter or discard unrelated changes.
- [x] M1-T002: Capture runtime status, global validation and workspace schema
  status, transition inspect/plan/apply support and any exact-pin release mismatch
  in `implementation.md`.
- [x] M1-T015: If the implementation runtime no longer satisfies
  `.p2p/project/runtime.yml`, run the existing runtime-contract update preview,
  obtain owner approval, apply through its supported command, verify runtime
  status and only then generate the workspace migration plan. Record any
  supported partial-failure recovery before proceeding.
- [x] M1-T003: Capture project vertical list/context, lock status, definition
  status, software vertical sections and current rubric state.
- [x] M1-T004: Capture domain/permissions/governance state and identify values
  currently supplied by compatibility fallback.
- [x] M1-T005: Capture project manifest bootstrap metadata requiring owner
  review without changing it.
- [x] M1-T006: Capture proposal artifact distribution, including vertical
  coverage absence and optional legacy artifact counts.
- [x] M1-T007: Build the decision index and record completeness, counts,
  diagnostic codes and affected sources.
- [x] M1-T008: Capture registry and rationalized project counts, assessment,
  maturity, progress and publication freshness.
- [x] M1-T009: Obtain explicit owner inputs for `software_project` or another
  vertical, profile, modules, owner identity, project status, workflow phase and
  current objective.
- [x] M1-T010: Prepare the structured migration input patch from approved owner
  values; keep assumptions explicit.
- [x] M1-T011: Run migration plan in text and JSON with no writes and archive the
  semantic plan fingerprint, source hashes and proposed preview tokens in
  `implementation.md`; do not archive secret owner-input values.
- [x] M1-T012: Review every canonical create/update, preserved legacy artifact,
  curation action and derived refresh action with the owner.
- [x] M1-T013: Re-run no-write plan after review changes and confirm stable
  fingerprint under repeated invocation and after any approved runtime-contract
  alignment.
- [x] M1-T014: M1 exit gate. Owner approves the exact apply inputs and no
  engine-prerequisite, runtime mismatch, unsupported or invalid blocker remains.

## M2 - Repository Project Definition Migration

- [x] M2-T001: Apply the approved workspace migration through the supported CLI
  using the reviewed fingerprint, confirmation and owner actor.
- [x] M2-T002: Immediately inspect transaction result, schema status, vertical
  lock, definition, rubrics, domain, permissions and project metadata.
- [x] M2-T003: Run global validation before any definition content patch.
- [x] M2-T004: Prepare the first definition patch for project vision/objective,
  system objective and success signal with source provenance; run definition
  preview and attach diff/source/result hashes to the owner review.
- [x] M2-T005: Obtain owner confirmation for M2-T004 content and apply through
  the stale-preview-protected definition apply primitive.
- [x] M2-T006: Prepare and apply owner-reviewed users/stakeholders and
  workflows/use-cases patch using a fresh preview token.
- [x] M2-T007: Prepare and apply owner-reviewed project scope, MVP boundaries and
  explicit non-goals patch using a fresh preview token.
- [x] M2-T008: Prepare and apply data model, lifecycle, integrations and
  dependency patch using current source evidence, preview/diff and explicit
  owner confirmation.
- [x] M2-T009: Prepare and apply constraints, NFR, acceptance and validation
  strategy patch using preview/diff and explicit owner confirmation.
- [x] M2-T010: Prepare and apply risks, assumptions, alternatives, owner
  decisions, milestones, definition of done and expected artifacts patch using
  preview/diff and explicit owner confirmation.
- [x] M2-T011: Leave unsupported claims missing/assumed/blocked with open
  questions; do not mark sections complete for presentation quality alone.
- [x] M2-T012: Run project definition show, project context, progress and global
  validation after each patch batch.
- [x] M2-T014: For every batch record source hash, semantic diff, result hash,
  preview token status, actor and apply result in `implementation.md`; do not
  retain owner-sensitive source content unnecessarily.
- [x] M2-T015: Before each apply, rerun preview if any source/definition hash has
  changed; assert stale tokens perform no write and stop the batch sequence on
  any unexpected diff.
- [x] M2-T013: M2 exit gate. Definition state is valid, every required section
  has an explicit truthful status, and owner-controlled unresolved content is
  visible; every applied batch has matching preview evidence.

## M3 - Repository Historical Relation Alignment

- [x] M3-T001: Rebuild the decision index after F6 and compare diagnostics with
  the M1 baseline before rewriting any source.
- [x] M3-T002: Confirm parser-state and collection-target diagnostics fixed by F6
  disappeared without artifact changes.
- [x] M3-T003: Group remaining relation diagnostics by unambiguous syntax,
  ambiguous semantics and invalid target.
- [x] M3-T004: Review PROP-100 relation terms such as `informs`, `constrained_by`
  and `enables`; record canonical direction/type decisions.
- [x] M3-T005: Review PROP-095 free-text future-workflow targets and decide
  whether each becomes a proposal, feature/capability relation or is removed.
- [x] M3-T006: Review remaining affected proposals in deterministic ID order and
  prepare bounded complete impact artifact replacement sets.
- [x] M3-T007: Validate each prepared artifact through the import path before
  replacement, review its complete diff and freeze the preview token.
- [x] M3-T008: Import one proposal batch, rebuild the index and inspect changed
  relations/evidence/diagnostics before continuing; use actor, confirmation and
  matching preview tokens for every import.
- [x] M3-T009: Repeat M3-T008 until approved relation corrections are complete;
  stop on unexpected retrieval or authority changes. Close the corresponding
  project-definition owner question and advance its next suggested action only
  through a separately previewed and owner-confirmed definition patch.
- [x] M3-T010: Resolve project conflict-memory corrections through the supported
  conflict preview/update-by-id workflow if any source-specific issue remains;
  do not append a contradictory duplicate record.
- [x] M3-T011: Record intentionally unsupported/ambiguous historical relations
  as residual follow-up rather than forcing lossy aliases.
- [x] M3-T013: Inject or simulate one invalid file and one stale source hash in a
  prepared batch and retain evidence that neither case changes any target before
  applying repository corrections.
- [x] M3-T014: Record actor, preview/result hashes and diagnostic delta for each
  impact/conflict correction batch in `implementation.md`.
- [x] M3-T012: M3 exit gate. No avoidable parser/list bug remains and every
  remaining partial diagnostic is intentional, source-specific and documented;
  no correction produced a partial artifact set.

## M4 - Repository Selective Vertical Coverage

- [x] M4-T001: Define first-batch selection criteria: foundational project
  identity, active Change Set/Work relevance, vertical/runtime governance and
  recent decision-memory work.
- [x] M4-T002: Produce the exact first proposal-id batch and record why each item
  is included; do not default to all 100 proposals.
- [x] M4-T003: Run vertical-coverage suggestions for the batch with no writes.
- [x] M4-T004: Review suggestions against the now-populated project definition;
  remove keyword-only false positives.
- [x] M4-T005: Add rationale and provenance to approved mappings and validate
  complete replacement payloads; review source/candidate hashes and semantic
  diff from coverage preview.
- [x] M4-T006: Import a small initial batch and verify validation, topology,
  evidence coverage, artifact-state provenance and retrieval behavior using
  actor, confirmation and matching preview tokens.
- [x] M4-T007: Continue in bounded batches only while M4-T006 gates remain clean.
  Regenerate previews whenever definition, proposal or coverage sources change.
- [x] M4-T008: Mark the non-reviewed remainder as legacy/unmapped in migration
  evidence, not by creating empty coverage artifacts.
- [x] M4-T009: Recompute project progress and confirm heuristic-only coverage is
  still reported separately.
- [x] M4-T011: Record each coverage preview/apply result and verify coverage plus
  artifact-state changed atomically; stop on any heuristic broad-match or
  provenance inconsistency.
- [x] M4-T010: M4 exit gate. Every materialized mapping is approved, valid and
  traceable with matching preview evidence; no bulk placeholder coverage exists.
  Close the corresponding project-definition owner question and clear or
  advance its next suggested action through a fresh reviewed definition patch.

## M5 - Repository Rebuild And Baseline Comparison

- [x] M5-T001: Run freshness status and freeze the ordered deterministic rebuild
  plan for every catalogued node after M2-M4 canonical changes.
- [x] M5-T002: Refresh registries and verify source proposal/change/choice/work
  counts.
- [x] M5-T003: Refresh rationalized project state and verify accepted proposal
  decision-map and feature counts match the shared committed lifecycle-authority
  policy, including `accepted_with_changes`, and obsolete owned projections are
  removed without touching unknown directories.
- [x] M5-T004: Rebuild decision context and record completeness, diagnostic
  delta, record/relation counts and representative retrieval results.
- [x] M5-T005: Refresh assessment and maturity/progress; verify outputs declare
  their basis and do not reproduce a false authoritative 100-percent state.
- [x] M5-T006: Refresh visible project export and publication preparation through
  supported commands after checking brief context/prompt, operational brief,
  next actions and per-change software-spec freshness/action requirements.
- [x] M5-T007: Re-run curator/validation/render stages only through their existing
  workflow; do not claim owner review or publication approval.
- [x] M5-T008: Run runtime status, workspace schema status, global validation,
  doctor, project status, compact context, vertical context, definition,
  progress and freshness checks; verify no active migration lock or scratch.
- [x] M5-T009: Run focused migration/decision/vertical/progress/freshness tests
  against the migrated repository where tests support real-root inspection.
- [x] M5-T010: Run the full repository test suite.
- [x] M5-T011: Compare post-migration evidence with M1: schema, vertical,
  definition, permissions/domain, derived counts, decision diagnostics,
  progress, brief/next-action/spec-export state and publication freshness.
- [x] M5-T012: Record residual legacy optional artifacts, intentionally unmapped
  proposals and deferred owner/curator actions.
- [x] M5-T013: Confirm Git diff contains only expected implementation, specs and
  supported migration outputs; do not revert unrelated user changes.
- [x] M5-T015: Verify workspace reports `layout_current` and separately records
  any residual semantic alignment advisory; do not convert intentional legacy or
  owner/curator work into a false fully-aligned result.
- [x] M5-T016: Record the final 94-item committed-authority basis (or the current
  live equivalent), owned-output reconciliation result, runtime compatibility,
  lock/scratch absence and every freshness-node delta in `implementation.md`.
- [x] M5-T014: M5 final gate. AC001-AC024 have direct evidence and the repository
  can operate on the current workspace schema without manual `.p2p` edits.

## Validation Evidence

Populate during implementation and migration. At minimum record:

- focused commands and pass counts for each F slice;
- full-suite command and pass count before M1 and after M5;
- representative legacy plan fingerprint and no-write evidence;
- semantic/physical hash evidence across different plan/apply dates;
- exclusive-lock, concurrency, durability, failure-injection and rollback results;
- definition, impact, conflict and coverage preview/apply token evidence;
- repository pre/post schema, diagnostics, counts, progress and freshness;
- runtime-contract alignment, owned-output reconciliation and lock/scratch
  absence;
- any deferred MCP write parity or owner/curator action.
