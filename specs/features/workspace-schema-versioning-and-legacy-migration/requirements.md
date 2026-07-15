# Requirements - Workspace Schema Versioning And Legacy Migration

## Scope

Introduce a reusable, versioned and inspectable migration lifecycle for `.p2p`
workspaces created by older P2P Engine releases. The lifecycle must distinguish
runtime compatibility from workspace-layout compatibility, produce a complete
read-only migration plan before writes, apply approved migrations safely, and
support the vertical, decision-memory and derived-state alignment required by
this repository.

This repository specification is implementation planning outside canonical P2P
proposal state. It does not select a project vertical, change owner decisions,
or mutate `.p2p` by itself.

## Delivery State

- Local implementation state: specification only.
- All implementation and repository-migration tasks are initially incomplete.
- Engine work must be completed and validated before repository-specific
  migration tasks begin.
- Repository migration tasks require explicit owner inputs where identified.

## Stable Work Identifiers

The identifiers from the original alignment plan are preserved:

- `F1`-`F9` identify reusable P2P Engine capabilities.
- `M1`-`M5` identify controlled migration work for this repository.
- Detailed tasks use `<work-id>-T<nnn>`, for example `F3-T004` or `M2-T003`.

The required delivery order is:

```text
F1 -> F2 -> F3 -> F6 -> {F4, F5, F7} -> {F8, F9}
   -> M1 -> {M2, M3, M4 in verified batches} -> M5
```

Braces mean the enclosed work may proceed in parallel after all preceding gates
pass. This order supersedes any later plain numeric restatement; it does not
renumber or replace the original `F*` and `M*` identifiers.

## Current Repository Baseline

The implementation and migration must account for this observed baseline:

- runtime contract `0.1.9` is compatible;
- structural validation currently reports zero errors and zero warnings;
- the project uses implicit `base_project` fallback;
- active vertical state, vertical lock and project definition state are absent;
- legacy software rubrics exist independently of the vertical runtime;
- stored assessment and maturity outputs predate recent accepted proposals;
- project-derived feature and decision-map state contains 82 entries while 94
  proposals have committed decision authority: 93 are `accepted` and one is
  `accepted_with_changes`;
- no proposal has declared `vertical-coverage.yml`;
- decision-context indexing is useful but partial because historical relation
  vocabulary and parsing conventions do not fully match current policies;
- current new-project initialization expects project domain and permission state
  that this legacy workspace does not materialize.

The baseline is evidence for this repository migration, not a hard-coded
assumption in the generic migration engine.

## In Scope

- An explicit workspace schema contract separate from package/runtime version.
- Read-only compatibility status and migration planning.
- Incremental registered migrations between adjacent workspace schema versions.
- Plan fingerprints, source preconditions, staging, rollback and crash recovery.
- Forward-only transition/runtime compatibility, exclusive apply locking and
  durable transaction journals.
- Action classification into automatic, owner-input, repository-curation,
  derived refresh and unsupported/manual-repair categories.
- Legacy vertical, definition, domain, permission and project-metadata planning.
- Decision-context compatibility fixes required before historical normalization.
- A supported proposal-to-vertical coverage write primitive.
- Preview/diff primitives for definition, impact, conflict and coverage writes
  used during semantic repository alignment.
- Separate project-definition completeness and evidence-coverage measures.
- Coordinated freshness inspection for derived project state and publications.
- CLI and JSON contracts for status, planning, apply and recovery.
- Additive migration visibility in doctor, project status, compact context and
  recommended-next-action surfaces.
- Read-only MCP status/plan parity after service and CLI contracts stabilize.
- Dogfooding the completed lifecycle on this repository through supported
  commands and owner-reviewed inputs.

## Out Of Scope

- Editing `.p2p` files manually as an upgrade mechanism.
- Inferring or recording owner decisions without explicit owner input.
- Automatically selecting a vertical during a read-only command.
- Automatically marking project-definition sections complete from keyword hits.
- Bulk materialization of modern optional artifacts for every historical
  proposal.
- Rewriting historical proposal or decision prose only to match a newer parser.
- Treating runtime package version as workspace schema version.
- Using Git reset, checkout or destructive repository operations as rollback.
- Network access, remote migrations or WaveKit server migration.
- A persistent database or migration cache.
- MCP migration apply in the first implementation; write parity requires a
  separately reviewed consent and recovery design.
- Automatically curating or approving human publication output.
- Workspace schema downgrades in the first implementation.

## Functional Requirements

### F1 - Workspace Schema Versioning

- F1-R001: THE SYSTEM SHALL define a workspace schema version independently of
  the installed P2P Engine runtime version and runtime compatibility contract.
- F1-R002: THE SYSTEM SHALL expose a versioned workspace schema state contract
  with contract version, current layout version, baseline/origin, applied
  migrations and last successful migration metadata.
- F1-R003: Fresh initialization SHALL write the current workspace schema state
  through the initialization service.
- F1-R004: A workspace without schema state SHALL be classified as
  `legacy_undeclared`, not silently treated as current.
- F1-R005: Schema-state reads SHALL distinguish missing, valid, invalid,
  unsupported, ahead-of-runtime and migration-incomplete states.
- F1-R006: Schema state SHALL be validated structurally and semantically with
  stable diagnostics and recovery commands.
- F1-R007: Existing runtime status and runtime contract behavior SHALL remain
  unchanged.
- F1-R008: Workspace schema status SHALL perform no persistent write.
- F1-R009: Schema status SHALL distinguish layout compatibility from semantic
  alignment advisories so a layout-current workspace is not reported as fully
  aligned while required owner or repository curation remains.
- F1-R010: Each current schema version SHALL declare the runtime versions or
  capabilities that can inspect, plan and apply transitions to it.
- F1-R011: Schema state and required migration/recovery actions SHALL be visible
  through additive global validation, doctor, project status, compact context
  and next-action outputs without changing existing required fields.

### F2 - Compatibility Analyzer And Migration Plan

- F2-R001: THE SYSTEM SHALL inspect the workspace once and build an immutable
  compatibility snapshot for one planning request.
- F2-R002: The analyzer SHALL inventory required, optional, legacy, generated,
  derived and unknown artifacts without treating optional legacy absence as a
  structural failure.
- F2-R003: The analyzer SHALL classify findings as `compatible`, `degraded`,
  `migration_required`, `owner_input_required`, `unsupported` or `invalid`.
- F2-R004: Every finding SHALL include a stable code, severity, affected path or
  logical object, reason, owning migration and supported recovery action.
- F2-R005: A migration plan SHALL contain ordered operations, dependencies,
  source hashes/preconditions, target schema version, write class,
  canonical/derived classification, reversibility and owner-input requirements.
- F2-R006: Planning SHALL produce a deterministic plan fingerprint from the
  source snapshot, selected migration path and supplied owner inputs.
- F2-R007: Text and JSON plan output SHALL expose equivalent semantics.
- F2-R008: Dry-run SHALL write no canonical, derived, temporary transaction or
  audit artifact.
- F2-R009: The plan SHALL explicitly distinguish engine-fix prerequisites from
  workspace operations that can be applied immediately.
- F2-R010: Unknown durable artifacts SHALL be reported and preserved unless an
  explicit migration owns them.
- F2-R011: The first migration planner SHALL support forward upgrades only and
  SHALL reject downgrade or lower-target requests before staging.
- F2-R012: Operation descriptors SHALL distinguish deterministic semantic
  candidate hashes from physical post-apply hashes containing audit-only fields.

### F3 - Transactional Migration Engine

- F3-R001: Migrations SHALL be registered as explicit adjacent transitions and
  SHALL NOT skip intermediate schema versions.
- F3-R002: Each migration SHALL declare an id, source version, target version,
  dependencies, planner, validator and apply implementation.
- F3-R003: Apply SHALL require explicit confirmation, an authorized actor and a
  matching plan fingerprint.
- F3-R004: Apply SHALL recompute source preconditions and refuse stale plans
  before writing.
- F3-R005: The engine SHALL render the complete candidate workspace overlay in a
  same-filesystem staging area before replacing managed files.
- F3-R006: The staged overlay SHALL pass migration-specific and global
  validation before commit.
- F3-R007: Multi-file apply SHALL maintain a transaction journal and original
  byte snapshots sufficient for deterministic rollback.
- F3-R008: The workspace schema marker and successful migration history SHALL be
  committed last.
- F3-R009: A handled failure SHALL restore original bytes and report whether
  rollback was complete.
- F3-R010: A crash-interrupted transaction SHALL be detected by status/doctor
  and SHALL require explicit resume or rollback.
- F3-R011: Applying an already completed migration SHALL be a no-op with an
  idempotent result.
- F3-R012: Migration logic SHALL NOT depend on Git availability or a clean Git
  worktree, although plan output MAY recommend a clean checkpoint.
- F3-R013: CLI presentation SHALL not contain migration domain logic.
- F3-R014: MCP apply SHALL remain unavailable in this feature.
- F3-R015: Apply and recovery SHALL acquire one exclusive workspace migration
  lock and SHALL reject or report concurrent migration attempts deterministically.
- F3-R016: Transaction scratch SHALL use a declared ignored internal root,
  restrictive permissions and durable journal/state writes without storing
  secrets or complete unrelated source documents.
- F3-R017: Whole-workspace staged validation SHALL read the candidate overlay for
  every migration-owned path and the live workspace only for preserved paths.
- F3-R018: Audit timestamps SHALL be fixed at apply time and SHALL NOT change
  reviewed plan identity or semantic candidate hashes.
- F3-R019: Apply SHALL recheck source and target preconditions after acquiring
  the exclusive lock and immediately before replacement begins.
- F3-R020: Successful apply, no-op and complete rollback SHALL leave no active
  lock or discoverable transaction scratch; unresolved recovery state SHALL
  remain visible through status and doctor.
- F3-R021: The runtime-contract update used to align an exact-pinned repository
  before migration SHALL reuse preview/stale-state and multi-file transaction
  guarantees or provide a tested complete recovery path before M1 may proceed.
- F3-R022: Commit SHALL verify each target's expected preimage immediately before
  replacing it; rollback SHALL not overwrite a target changed by an external
  writer after migration replacement and SHALL enter explicit recovery instead.
- F3-R023: While a migration lock is active, all other governed workspace write
  preflights SHALL fail closed except the matching recovery operation; read-only
  status and inspection SHALL remain available.
- F3-R024: Because planning is no-write, apply SHALL receive the target version
  and owner-input payload again, normalize and recompute the plan, and compare
  the reviewed fingerprint before acquiring write ownership.

### F6 - Decision-Context Legacy Compatibility

- F6-R001: Decision parsing SHALL resolve lifecycle state from recognized state
  tokens, preferring the `Status` section over free-form `Outcome` prose.
- F6-R002: Free-form decision outcome text SHALL remain indexed as decision
  content and SHALL NOT become an unknown lifecycle state solely because it is
  present under `Outcome`.
- F6-R003: Pending draft decisions SHALL remain unresolved evidence without
  being treated as corrupt source state.
- F6-R004: Conflict normalization SHALL parse scalar and collection-valued
  winner/rejected fields without stringifying collections.
- F6-R005: The relation vocabulary and alias map SHALL be versioned data.
- F6-R006: Existing unambiguous historical terms SHALL map through tested
  compatibility aliases without rewriting canonical artifacts.
- F6-R007: Ambiguous relation terms SHALL remain diagnostics until an explicit
  semantic mapping is supplied.
- F6-R008: Proposal relation validation SHALL distinguish proposal IDs from
  capability/surface/feature identifiers and unsupported free-text targets.
- F6-R009: Impact artifact import SHALL validate relation vocabulary and target
  shape before replacing an existing artifact.
- F6-R010: Compatibility fixes SHALL reduce avoidable index diagnostics without
  mutating source artifacts during index build.
- F6-R011: The source catalog and retrieval output SHALL remain deterministic
  after alias-policy changes.
- F6-R012: Multi-artifact impact correction SHALL validate and preview the
  complete replacement set before any target changes and SHALL commit atomically
  with actor, confirmation, source hashes and audit evidence.
- F6-R013: Project conflict memory SHALL expose read-only preview and a narrow
  update-by-conflict-id primitive; correction SHALL NOT be implemented by
  appending a contradictory replacement record.

### F4 - Vertical Migration

- F4-R001: The planner SHALL detect legacy workspaces with project domain or
  software evidence but no explicit active vertical.
- F4-R002: The planner MAY recommend candidate verticals but SHALL require owner
  selection before apply.
- F4-R003: Vertical migration SHALL stage active state, resolved lock, initial
  definition state and migrated rubrics as one transaction.
- F4-R004: The selected vertical SHALL be resolved and checksummed before any
  workspace file changes.
- F4-R005: Existing rubric enabled/disabled choices SHALL be preserved by stable
  criterion identity where semantics match.
- F4-R006: Unmapped legacy rubric criteria SHALL be preserved as legacy evidence
  but excluded from active vertical-baseline scoring until explicitly mapped or
  enabled under a supported policy.
- F4-R007: Migration SHALL NOT silently delete legacy criteria.
- F4-R008: Initial definition state SHALL preserve missing, blocked and unknown
  information; it SHALL NOT infer completion from proposal keywords.
- F4-R009: Ordinary reads SHALL continue to avoid implicit migration.
- F4-R010: Project-definition patching SHALL expose a no-write preview containing
  validated operations, semantic diff, source hash and resulting definition hash.
- F4-R011: Explicit ordinary vertical selection SHALL reuse complete candidate
  rendering/validation and SHALL not leave a partial active/lock/definition/
  rubric state after a handled write failure.

### F5 - Legacy Domain, Permissions And Metadata Bootstrap

- F5-R001: The planner SHALL detect missing explicit domain and permissions
  artifacts expected by current initialization.
- F5-R002: Domain state MAY be seeded from a valid project manifest domain with
  explicit provenance.
- F5-R003: Permission state MAY be seeded from valid legacy governance roles and
  explicit owner identity input.
- F5-R004: Conflicting or missing owner identities SHALL block permission
  materialization.
- F5-R005: Stale bootstrap metadata SHALL be reported separately from structural
  migration and SHALL require an owner-provided structured metadata patch.
- F5-R006: The system SHALL provide a narrow validated metadata update path; it
  SHALL NOT expose arbitrary project-manifest YAML replacement.
- F5-R007: Re-running project initialization SHALL NOT be the required migration
  mechanism for existing workspaces.
- F5-R008: Existing remote and repository configuration SHALL be preserved
  unless explicitly included in the owner patch.
- F5-R009: Metadata patching SHALL expose preview, actor authority, confirmation,
  stale-preview protection and an audit record for changed allowed fields.

### F7 - Proposal Vertical Coverage Primitive

- F7-R001: THE SYSTEM SHALL expose read-only show/status for proposal vertical
  coverage.
- F7-R002: THE SYSTEM SHALL expose a suggestion operation that returns candidate
  section mappings, confidence and evidence without writing.
- F7-R003: Heuristic suggestions SHALL NOT be treated as declared topology.
- F7-R004: THE SYSTEM SHALL expose a validated set/import operation for an exact
  proposal id, vertical id and section mapping.
- F7-R005: Set/import SHALL validate active/resolvable vertical, section ids,
  rationale, source and provenance before writing atomically.
- F7-R006: Existing schema-version-1 coverage artifacts SHALL remain readable.
- F7-R007: New coverage writes SHALL carry additive provenance sufficient to
  distinguish owner-confirmed, agent-proposed and migrated mappings.
- F7-R008: Artifact-state integration SHALL classify vertical coverage as
  `required_when_applicable`, not required for every legacy proposal.
- F7-R009: CLI and MCP read contracts SHALL be JSON-equivalent; MCP write parity
  MAY be added only through the existing write-safe import boundary.
- F7-R010: Suggestion policy SHALL use section-specific evidence, token/phrase
  boundaries and confidence thresholds and SHALL suppress broad keyword-only
  matches known to map most proposals to the same section.
- F7-R011: Coverage import SHALL expose a no-write preview and require actor,
  confirmation and matching source/candidate hashes before replacement.
- F7-R012: Coverage artifact and artifact-state provenance SHALL commit as one
  atomic operation or both remain unchanged.

### F8 - Progress Model Convergence

- F8-R001: THE SYSTEM SHALL compute project-definition completeness separately
  from proposal/evidence coverage.
- F8-R002: Definition completeness SHALL report required section status,
  required field completion, blockers, assumptions and open questions.
- F8-R003: Fieldless required sections SHALL be measured by explicit section
  status rather than keyword matches.
- F8-R004: Evidence coverage SHALL distinguish declared mappings from heuristic
  suggestions and accepted evidence from draft/historical evidence.
- F8-R005: The system SHALL NOT collapse the two axes into an unexplained single
  project-progress score.
- F8-R006: Any percentage SHALL expose numerator, denominator, exclusions and
  policy version.
- F8-R007: Legacy maturity output SHALL identify its keyword/rubric basis and
  SHALL NOT claim authoritative project-definition completeness.
- F8-R008: Project readiness SHALL consume definition state and declared
  coverage while reporting heuristic matches separately.
- F8-R009: CLI and JSON output SHALL expose the same progress state.
- F8-R010: Missing definition state SHALL produce `not_initialized`, not zero or
  one hundred percent completion.

### F9 - Derived-State Freshness

- F9-R001: THE SYSTEM SHALL model freshness dependencies among canonical source,
  registries, rationalized project state, decision context, assessment,
  maturity, exports and publication stages.
- F9-R002: Freshness SHALL use content/source fingerprints where available and
  deterministic source counts/hashes otherwise.
- F9-R003: The system SHALL report mixed states such as fresh registries with a
  stale decision map.
- F9-R004: Freshness output SHALL include an ordered rebuild plan and identify
  deterministic versus owner/curator-dependent stages.
- F9-R005: Read-only freshness inspection SHALL perform no rebuild.
- F9-R006: Deterministic refresh orchestration MAY call existing supported
  refresh services but SHALL stop before owner review or curator approval.
- F9-R007: Derived refresh SHALL occur only after canonical migration commits.
- F9-R008: Publication SHALL remain stale until its existing pipeline is rerun;
  migration SHALL NOT mark it current artificially.
- F9-R009: The initial freshness graph SHALL explicitly classify registries,
  project projections, decision context, assessment, maturity/progress,
  operational brief inputs/output, next actions, software-spec exports, visible
  exports and every publication stage.
- F9-R010: Derived proposal projections SHALL use one shared lifecycle-authority
  policy, including `accepted_with_changes`, rather than an exact string test for
  `accepted`.
- F9-R011: Derived refresh SHALL reconcile the exact service-owned output set,
  remove stale owned outputs and preserve unknown or non-owned artifacts.
- F9-R012: Freshness orchestration SHALL report agent-curated and owner-controlled
  nodes but SHALL NOT overwrite or approve them automatically.

### M1 - Repository Baseline And Owner Inputs

- M1-R001: Capture a machine-readable pre-migration baseline for this repository
  after all engine capability gates pass.
- M1-R002: Obtain explicit owner selection for vertical, profile, modules,
  project phase, current objective and owner identity.
- M1-R003: Generate a no-write migration plan and review every planned canonical
  and derived operation.
- M1-R004: No repository apply may begin while the plan contains unresolved
  engine prerequisites, invalid sources or ambiguous owner inputs.
- M1-R005: If the implementation release no longer satisfies the repository's
  exact runtime contract, the owner SHALL preview and apply a supported runtime
  contract update before freezing the workspace migration plan.

### M2 - Project Definition Migration

- M2-R001: Apply the approved vertical/domain/permission migration through the
  generic engine.
- M2-R002: Populate project definition fields through structured patches with
  explicit source provenance.
- M2-R003: Owner-controlled content SHALL be confirmed before affected sections
  are marked complete.
- M2-R004: Missing evidence SHALL remain missing, assumed or blocked rather than
  being filled with generated prose presented as fact.
- M2-R005: Every definition patch batch SHALL be previewed, diffed and confirmed
  against its source and candidate hashes before apply.

### M3 - Historical Relation Alignment

- M3-R001: Rebuild the decision index after F6 without source rewrites and record
  the remaining genuinely source-specific diagnostics.
- M3-R002: Review ambiguous relationship terms and free-text targets proposal by
  proposal.
- M3-R003: Apply approved relation corrections through supported artifact import
  or update primitives.
- M3-R004: Preserve historical meaning and evidence while normalizing syntax.
- M3-R005: Relation and conflict corrections SHALL use previewable, atomic,
  actor-attributed supported primitives.

### M4 - Selective Vertical Coverage

- M4-R001: Define an initial proposal batch based on foundational relevance,
  current activity and recent vertical/runtime work.
- M4-R002: Generate suggestions for the batch and review them against project
  definition sections.
- M4-R003: Import only approved mappings with provenance.
- M4-R004: Leave non-reviewed historical proposals explicitly legacy/unmapped;
  absence is not an error by itself.
- M4-R005: Every coverage batch SHALL be reviewed from a no-write preview and
  imported with matching hashes and provenance.

### M5 - Rebuild And Baseline Comparison

- M5-R001: Refresh deterministic derived state in the dependency order reported
  by F9.
- M5-R002: Recompute assessment, maturity/progress and decision context after
  canonical changes.
- M5-R003: Rerun project export/publication preparation without claiming owner
  review or publication approval.
- M5-R004: Compare post-migration counts, diagnostics, freshness and progress
  against the M1 baseline.
- M5-R005: Record residual intentional legacy states and follow-up work instead
  of hiding them.
- M5-R006: Final verification SHALL include runtime contract compatibility,
  absence of active migration lock/scratch and layout-versus-semantic alignment.
- M5-R007: Baseline comparison SHALL include every initial freshness node and the
  lifecycle-authority basis used for proposal-derived counts.

## Non-Functional Requirements

- N001: Domain behavior SHALL live in cohesive services behind `P2PWorkspace`;
  the facade receives delegation only.
- N002: Structured parsing SHALL use YAML/Markdown parsers and typed contracts,
  not ad hoc text replacement.
- N003: Read-only status, plan, suggestion and freshness operations SHALL be
  proven mutation-free.
- N004: Plan and result serialization SHALL be deterministic under reversed file
  enumeration.
- N005: Migration apply SHALL be testable with injected filesystem failures at
  every replacement boundary.
- N006: Stable diagnostic and migration identifiers SHALL be versioned public
  data once released.
- N007: Existing CLI commands and MCP payloads SHALL remain backward compatible
  unless this feature explicitly adds a new command or additive field.
- N008: CLI text and JSON output SHALL share one service result model.
- N009: No network access SHALL be required.
- N010: Migration of a representative 100-proposal workspace SHALL remain
  bounded and SHALL avoid per-proposal full workspace rescans.
- N011: Security checks SHALL reject path traversal, symlink escape and migration
  operations outside declared project targets.
- N012: Migration logs and diagnostics SHALL avoid embedding secrets or entire
  source documents.
- N013: Every slice SHALL have focused tests before dependent work starts.
- N014: Repository dogfooding SHALL not be used as a substitute for synthetic
  fresh, legacy, malformed and interrupted-transaction tests.
- N015: Apply/recovery locking SHALL be process-safe and testable with two
  independent service instances.
- N016: Transaction durability SHALL include file and containing-directory sync
  where the platform supports it; unsupported guarantees SHALL be explicit.
- N017: Transaction scratch SHALL not be discovered as canonical, derived,
  unknown durable or registry input during planning, validation or recovery.
- N018: Plan fingerprints SHALL be semantic and stable while physical result
  hashes and audit timestamps remain inspectable separately.
- N019: Durable implementation and migration evidence for this feature SHALL be
  recorded only in
  `specs/features/workspace-schema-versioning-and-legacy-migration/implementation.md`.
- N020: Every new semantic write primitive SHALL share one result model across
  preview/apply and SHALL reject stale previews without changing targets.
- N021: Preview/apply SHALL NOT depend on a hidden persistent preview cache;
  apply receives the candidate input again and recomputes token semantics.

## Edge Cases And Failure Semantics

- E001: Missing schema state with otherwise valid legacy files produces a plan,
  not an automatic write.
- E002: Workspace schema version newer than the runtime fails closed.
- E003: Missing intermediate migration blocks apply with an actionable error.
- E004: Source content changes after planning invalidate the fingerprint.
- E005: Staging validation failure leaves the workspace untouched.
- E006: Replacement failure triggers rollback and reports changed/restored paths.
- E007: Rollback failure leaves an explicit interrupted transaction requiring
  recovery; it is never reported as success.
- E008: Existing interrupted transaction blocks a new migration.
- E009: Active vertical id cannot resolve or checksum validation fails; vertical
  migration writes nothing.
- E010: Legacy rubric id collides with a new criterion but semantics differ;
  migration requires explicit mapping.
- E011: No owner identity can be derived; permission migration blocks.
- E012: Decision file contains free-form Outcome and recognized Status; Status
  controls lifecycle and Outcome remains content.
- E013: Relation alias is ambiguous; index emits diagnostic and migration plan
  requests semantic input.
- E014: Coverage suggestion returns no confident section; no empty artifact is
  written.
- E015: Project definition is missing; progress reports not initialized.
- E016: Registry refresh succeeds but project refresh fails; freshness reports a
  mixed partial state and preserves the failure.
- E017: Publication requires curation/review; deterministic refresh stops before
  owner-dependent stages.
- E018: Two concurrent apply attempts target the same workspace; exactly one may
  acquire the migration lock and the other performs no write.
- E019: Requested target schema is lower than current; planning returns an
  unsupported-downgrade diagnostic and creates no transaction state.
- E020: Installed runtime can inspect but cannot apply the selected transition;
  status remains readable and apply reports the required runtime action.
- E021: Plan and apply run on different dates; audit timestamps differ from plan
  time without invalidating an otherwise unchanged semantic fingerprint.
- E022: A multi-file impact correction contains one invalid artifact; no impact
  or related-proposal target changes.
- E023: A proposal leaves the committed lifecycle set; project refresh removes
  only its owned derived feature projection and preserves unrelated directories.
- E024: A non-cooperating editor changes a target between staging and its replace
  boundary; commit stops before overwriting it and reports stale target state.
- E025: Another governed write command starts while migration apply/recovery owns
  the lock; it is rejected before its service mutates workspace state.
- E026: Apply omits or changes owner input used during plan/preview; fingerprint
  or preview-token comparison fails before lock acquisition or target writes.

## Acceptance Criteria

- AC001: Runtime compatibility and workspace schema compatibility are reported
  independently.
- AC002: A legacy fixture receives a deterministic, complete no-write plan.
- AC003: Successful migration reaches the current schema through adjacent
  migrations and a second apply is a no-op.
- AC004: Injected failures prove pre-write validation, rollback and interrupted
  recovery behavior.
- AC005: Decision-context legacy fixtures parse recognized status, collection
  conflicts and supported aliases without avoidable partial diagnostics.
- AC006: Ambiguous relations remain explicit diagnostics until curated.
- AC007: Vertical migration produces coherent active state, lock, definition and
  rubric state or writes nothing.
- AC008: Missing domain and permission artifacts can be materialized from valid
  legacy evidence plus owner input without rerunning init.
- AC009: Vertical coverage can be suggested without writes and imported through
  a validated supported primitive.
- AC010: Progress exposes definition completeness and evidence coverage as
  separate, explainable axes.
- AC011: Freshness detects divergent derived layers and orders rebuild work.
- AC012: This repository produces an owner-reviewable dry-run before canonical
  migration.
- AC013: Post-migration project-derived accepted proposal counts match live
  accepted proposal state.
- AC014: Post-migration decision-context diagnostics contain no parser bug,
  collection-stringification bug or unreviewed unsupported alias that the
  versioned policy claims to support.
- AC015: No task relies on manual `.p2p` editing.
- AC016: Focused tests, full tests, `p2p validate`, migration status and
  post-migration freshness all pass their documented gates.
- AC017: Concurrent apply, crash recovery and directory-durability tests prove
  exclusive ownership and leave no hidden active transaction after success.
- AC018: Definition, impact, conflict and coverage corrections have deterministic
  no-write previews and stale-preview-protected apply paths.
- AC019: Doctor, project status, compact context and next actions expose required
  migration or recovery work without mutating the workspace.
- AC020: Derived refresh uses shared lifecycle authority, reconciles owned output
  sets and reports freshness for operational brief, next actions and spec exports.
- AC021: Runtime-contract release alignment cannot leave setup guidance and the
  canonical runtime contract silently inconsistent after a handled failure.
- AC022: Per-target preimage and rollback-ownership tests prove migration never
  silently overwrites a concurrent external edit.
- AC023: Every governed write boundary observes the migration lock while all
  required read-only diagnostics continue to work.
- AC024: Migration and semantic mutation apply paths recompute from resupplied
  inputs and require no durable preview cache.
