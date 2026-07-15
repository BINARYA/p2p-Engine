# Design - Workspace Schema Versioning And Legacy Migration

## Requirements Covered

- `F1-R001` through `F1-R011`
- `F2-R001` through `F2-R012`
- `F3-R001` through `F3-R024`
- `F4-R001` through `F4-R011`
- `F5-R001` through `F5-R009`
- `F6-R001` through `F6-R013`
- `F7-R001` through `F7-R012`
- `F8-R001` through `F8-R010`
- `F9-R001` through `F9-R012`
- `M1-R001` through `M1-R005`
- `M2-R001` through `M2-R005`
- `M3-R001` through `M3-R005`
- `M4-R001` through `M4-R005`
- `M5-R001` through `M5-R007`
- `N001` through `N021`
- `E001` through `E026`
- `AC001` through `AC024`

## Design Goals

1. Make workspace layout compatibility explicit and independent of runtime
   package compatibility.
2. Turn upgrades into deterministic plans and registered transitions rather
   than scattered repair commands.
3. Guarantee that read-only inspection never materializes missing state.
4. Validate a complete candidate state before canonical files change.
5. Preserve owner authority for vertical, identity, metadata and semantic
   relation choices.
6. Fix generic compatibility defects before rewriting historical artifacts.
7. Make project progress and derived freshness explainable rather than inferred
   from one optimistic score.
8. Use this repository as an end-to-end migration case without hard-coding its
   history into the engine.
9. Make concurrent apply, crash recovery and post-crash diagnostics explicit
   operational contracts rather than best-effort filesystem behavior.
10. Provide reviewable semantic correction primitives for every repository
    artifact that M2-M4 must change.

## Identifier And Delivery Contract

Capability identifiers are stable and retain their original meaning:

| ID | Capability |
| --- | --- |
| F1 | Workspace schema versioning |
| F2 | Compatibility analyzer and dry-run plan |
| F3 | Transactional migration engine |
| F4 | Vertical migration |
| F5 | Domain, permissions and metadata bootstrap |
| F6 | Decision-context legacy compatibility |
| F7 | Proposal vertical-coverage primitive |
| F8 | Progress model convergence |
| F9 | Derived-state freshness |
| M1 | Repository baseline and owner inputs |
| M2 | Repository project-definition migration |
| M3 | Repository historical relation alignment |
| M4 | Repository selective vertical coverage |
| M5 | Repository rebuild and baseline comparison |

Required order:

```text
Foundation:       F1 -> F2 -> F3
Compatibility:   F3 -> F6
State surfaces:  F6 -> F4, F5, F7
Interpretation:  F4/F5/F7 -> F8, F9
Dogfooding:      F8/F9 -> M1 -> M2/M3/M4 -> M5
```

## Key Decisions

- D001: Workspace schema version is a layout/data-contract version, not the P2P
  package version and not `.p2p/project/runtime.yml`.
- D002: Missing schema state means `legacy_undeclared`. Reads never adopt or
  migrate it implicitly.
- D003: Migration planning is a pure operation over one immutable source
  snapshot. Apply binds to its fingerprint and recomputes preconditions.
- D004: Migrations are adjacent registered transitions. A runtime cannot claim
  compatibility when an intermediate transition is unavailable.
- D005: Candidate files are rendered and validated in staging. Canonical
  replacements begin only after the complete candidate overlay is valid.
- D006: Multi-file safety uses a journal plus original-byte snapshots and
  deterministic rollback. Workspace schema history is committed last.
- D007: Owner-required values are typed plan inputs, never inferred writes.
- D008: F6 precedes historical artifact correction. Parser and alias defects are
  fixed once in code instead of rewriting valid legacy evidence repeatedly.
- D009: Vertical selection and its four state outputs become one migration
  operation rather than four independently committed writes.
- D010: Legacy rubric criteria are never silently deleted. Unmapped criteria are
  visible but excluded from active vertical-baseline scoring.
- D011: Vertical-coverage suggestions are heuristic evidence. Only validated
  imported mappings become topology relations.
- D012: Progress is a multi-axis derived view. Definition completeness and
  evidence coverage remain separate even when a UI later summarizes them.
- D013: Freshness inspection is read-only. Deterministic rebuild orchestration
  stops before curator or owner-controlled approval.
- D014: CLI is the first migration apply surface. MCP receives read-only status
  and planning after contracts stabilize; write parity is deferred.
- D015: Repository-specific M tasks are acceptance work, not hidden logic in
  generic migration classes.
- D016: Workspace schema v1 is forward-only. A lower requested target is an
  unsupported operation, never an implicit rollback or downgrade.
- D017: Every transition declares the engine version/capability range that may
  inspect, plan and apply it. Runtime-contract compatibility remains a separate
  owner-controlled repository contract.
- D018: `current_version` reports layout compatibility only. Semantic alignment
  advisories and unresolved owner/curation work are derived status dimensions,
  not fabricated migration-history entries.
- D019: Apply and recovery use one process-safe exclusive workspace lock. Source
  preconditions are checked again under that lock before replacement.
- D020: Whole-overlay validation uses a candidate workspace view. A validator
  must not accidentally reread a migration-owned live target.
- D021: Plan identity uses semantic candidate hashes. Apply-time timestamps and
  physical file hashes are result evidence and cannot invalidate an unchanged
  reviewed plan.
- D022: Transaction scratch is private, ignored by discovery and durable enough
  for explicit recovery. Successful apply/no-op/rollback removes lock and
  scratch; unresolved recovery retains both discoverable evidence and guidance.
- D023: Definition, impact, conflict and coverage mutation use preview tokens,
  actor authority, explicit confirmation and stale-preview rejection.
- D024: Derived project projections use shared lifecycle authority and reconcile
  only exact service-owned outputs; file existence alone never proves freshness.
- D025: The migration lock participates in the common governed-write preflight.
  It coordinates engine writes, while per-target preimage checks protect against
  non-cooperating external editors.
- D026: Plans and mutation previews are stateless capabilities, not stored
  approvals. Apply receives the same logical input again and recomputes the
  fingerprint/token before any write ownership is acquired.

## Proposed Module Boundaries

Exact filenames may be consolidated to match local code ownership, but these
responsibilities must remain independently testable.

### Core Workspace Schema Contracts

`src/p2p_engine/core/workspace_schema.py`

- workspace schema states and versions;
- migration identifiers and transition metadata;
- compatibility finding and severity types;
- plan operation, plan input, plan and fingerprint contracts;
- transaction, rollback and recovery result types;
- runtime/capability support metadata, lock state and semantic/physical hashes;
- deterministic JSON-ready serialization.

This module contains no filesystem reads or writes.

### Workspace Compatibility Service

`src/p2p_engine/services/workspace_compatibility.py`

- captures one workspace inventory snapshot;
- reads and validates workspace schema state;
- identifies legacy/missing/current/unsupported artifacts;
- reports layout state separately from semantic alignment advisories;
- invokes migration planners without applying them;
- classifies owner inputs and engine prerequisites;
- computes deterministic plan fingerprints.

The service reuses structured readers from existing services where possible. It
must not implement a second parser for vertical, permission, proposal or
decision artifacts.

### Workspace Migration Registry

`src/p2p_engine/services/workspace_migration_registry.py`

- registers adjacent transitions;
- records inspect/plan/apply engine requirements per transition;
- validates duplicate ids, version gaps and unsupported direction changes;
- resolves a source-to-target migration path;
- exposes migration metadata to status and planning;
- rejects cycles or ambiguous paths.

Registration is code-owned and deterministic. Project files cannot inject
executable migration implementations.

### Workspace Migration Engine

`src/p2p_engine/services/workspace_migrations.py`

- validates actor, confirmation and plan fingerprint;
- acquires the exclusive migration lock and recomputes preconditions under it;
- creates same-filesystem staging and transaction journal;
- asks registered migrations to render candidate files;
- validates the staged overlay;
- commits replacements in deterministic order with durable file/directory sync;
- commits schema/history state last;
- rolls back or exposes explicit recovery state.

`P2PWorkspace` delegates to these services and contains no planning or rollback
rules.

The common workspace write preflight checks active migration ownership before
delegating to any governed mutation service. Only the recovery operation bound
to the lock transaction id may write while recovery is required.

### Candidate Workspace View

`src/p2p_engine/services/candidate_workspace.py`

- resolves migration-owned paths from staged candidates;
- resolves preserved paths from the captured live snapshot;
- rejects undeclared writes, path escapes and symlink traversal;
- provides the same structured reader interface expected by validators;
- records every read so tests can prove candidate validation never falls back to
  a stale live target.

The candidate view is request-scoped. It is not a persistent virtual filesystem
and never becomes another source of truth.

### Shared Mutation Preview Contracts

`src/p2p_engine/core/mutation_preview.py`

- normalized operation id and target set;
- actor/authority and confirmation requirements;
- source hashes and missing markers;
- deterministic semantic diff and candidate hashes;
- policy version, expiry policy and stale-preview token;
- apply result with final physical hashes and audit metadata.

Definition, metadata, impact, conflict and coverage primitives reuse this shape.
The token is a canonical hash of operation, targets, source preconditions,
candidate semantics and policy version; it never embeds source contents or
secrets.

### Project Alignment Collaborators

Existing services remain owners of their formats:

- `ProjectVerticalService`: vertical resolution, lock, definition and rubric
  candidate rendering;
- `ProjectMaturityService`: rubric compatibility and legacy-score labeling;
- permissions/governance services: explicit permission materialization;
- project initialization/domain services: domain candidate rendering;
- proposal artifact service: related-proposal and vertical-coverage import;
- conflict-memory service: preview and narrow update-by-id;
- decision-context services: parser, authority and relation compatibility;
- project state/registry/publication services: freshness and rebuild actions.

Migration code orchestrates these owners through pure render/validate methods;
it does not duplicate their schemas.

### Progress Service

`src/p2p_engine/services/project_progress.py`

- computes definition section and required-field completeness;
- computes declared evidence coverage separately;
- exposes blockers, assumptions and questions;
- labels heuristic suggestions separately;
- provides policy versions, numerators and denominators.

The first implementation is read-only and request-scoped.

### Derived Freshness Service

`src/p2p_engine/services/derived_freshness.py`

- defines the derived dependency graph;
- captures current fingerprints/counts;
- reports current, stale, missing, partial and owner-action-required nodes;
- returns an ordered rebuild plan;
- optionally orchestrates only deterministic existing refresh operations.

It also owns a versioned lifecycle-authority projection policy and an exact
manifest of service-owned derived outputs. It may remove a stale owned output;
it must preserve unknown directories and owner/agent-authored artifacts.

## Service Primitive Catalog

Names may follow local naming conventions, but the following typed operations
must exist behind `P2PWorkspace` and must not be implemented in CLI handlers:

```text
WorkspaceSchemaService.status() -> WorkspaceSchemaStatus
WorkspaceCompatibilityService.snapshot() -> CompatibilitySnapshot
WorkspaceCompatibilityService.plan(target, owner_inputs) -> MigrationPlan

WorkspaceMigrationService.apply(target, owner_inputs, plan_fingerprint, actor, confirm) -> ApplyResult
WorkspaceMigrationService.recovery_status() -> RecoveryStatus
WorkspaceMigrationService.rollback(transaction_id, actor, confirm) -> RecoveryResult
WorkspaceMigrationService.resume(transaction_id, actor, confirm) -> RecoveryResult

MutationPreviewService.token(operation, targets, sources, candidate, policy) -> str
MigrationLockService.acquire(transaction_id) -> MigrationLock
MigrationLockService.release(transaction_id) -> None

ProjectVerticalService.render_migration_candidate(selection) -> VerticalCandidate
ProjectVerticalService.preview_definition_patch(patch) -> MutationPreview
ProjectVerticalService.apply_definition_patch(patch, preview_token, actor, confirm) -> MutationResult

ProjectMetadataService.preview_patch(patch) -> MutationPreview
ProjectMetadataService.apply_patch(patch, preview_token, actor, confirm) -> MutationResult

ProposalArtifactService.preview_impact(proposal_id, artifact_set) -> MutationPreview
ProposalArtifactService.apply_impact(proposal_id, artifact_set, preview_token, actor, confirm) -> MutationResult

ConflictMemoryService.preview_update(conflict_id, patch) -> MutationPreview
ConflictMemoryService.update(conflict_id, patch, preview_token, actor, confirm) -> MutationResult

ProposalVerticalCoverageService.show(proposal_id) -> CoverageStatus
ProposalVerticalCoverageService.suggest(proposal_id) -> CoverageSuggestion
ProposalVerticalCoverageService.preview_import(proposal_id, payload) -> MutationPreview
ProposalVerticalCoverageService.import_coverage(proposal_id, payload, preview_token, actor, confirm) -> MutationResult

ProjectProgressService.status() -> ProjectProgress
DerivedFreshnessService.status() -> FreshnessStatus
DerivedFreshnessService.rebuild_plan() -> RebuildPlan
DerivedFreshnessService.refresh_deterministic(confirm) -> RebuildResult
```

`refresh_deterministic` remains optional in v1; `status` and `rebuild_plan` are
mandatory. Preview is no-write and creates no durable token cache. Apply receives
the candidate input again, reparses it through the owner service, recomputes the
source/candidate semantics and compares the reviewed token.

## Workspace Schema State

The proposed durable state path is:

```text
.p2p/project/workspace-schema.yml
```

Proposed shape:

```yaml
workspace_schema:
  contract_version: 1
  current_version: 1
  baseline: migrated_legacy
  initialized_at: 2026-07-15
  initialized_by: owner
  applied_migrations:
    - id: workspace-legacy-to-v1
      from: legacy_undeclared
      to: 1
      applied_at: 2026-07-15
      actor: owner
      plan_fingerprint_sha256: "..."
```

The contract records successful transitions only. In-progress transaction data
does not belong in this file.

Fresh projects write the current version with `baseline: initialized_current`
and an empty applied migration list.

`initialized_at`, `applied_at` and actor values are audit evidence fixed during
apply. They are excluded from plan identity. The state parser verifies that
applied migrations form a contiguous registered path ending at
`current_version`; duplicate, unknown or out-of-order history is invalid.

## Compatibility Dimensions And Transition Support

Status is derived on two independent dimensions:

- `layout_status`: legacy, current, ahead, invalid, unsupported or incomplete;
- `alignment_status`: aligned, degraded, owner_input_required,
  repository_curation_required or recovery_required.

A workspace may therefore be `layout_status=current` and
`alignment_status=degraded`. The durable schema marker never claims that
optional historical artifacts were semantically curated.

Every registered transition declares:

- source and target workspace schema versions;
- minimum/maximum engine versions or named capabilities for inspect, plan and
  apply;
- forward direction and whether a future separately designed downgrade exists;
- required owner inputs and validators.

The initial registry contains no downgrade. An engine that can inspect but not
apply a transition returns status and an actionable runtime prerequisite rather
than making the workspace unreadable.

## Compatibility Snapshot

One planning request produces an immutable snapshot containing:

- normalized root and project identity;
- workspace schema state and runtime status;
- known artifact presence, hashes and classifications;
- active/fallback vertical, lock and definition state;
- domain, permission, governance and metadata state;
- proposal artifact generation distribution;
- decision-context diagnostic summary;
- derived-state fingerprints and counts;
- unknown managed-root files;
- source-access counters.

The snapshot captures bytes once for files consumed by multiple planners. Hashes
and parsing must use those captured bytes.

## Finding And Action Classification

Findings use these states:

- `compatible`: no action required;
- `degraded`: supported fallback reduces capability;
- `migration_required`: registered automatic transition exists;
- `owner_input_required`: supported operation exists but values require owner
  authority;
- `repository_curation_required`: semantic source correction is needed;
- `engine_prerequisite_required`: apply is blocked until a code capability is
  implemented or upgraded;
- `unsupported`: no safe migration path exists;
- `invalid`: current data violates a known contract.

Plan operations use these kinds:

- `create_canonical`;
- `update_canonical`;
- `preserve_legacy`;
- `quarantine_legacy`;
- `refresh_derived`;
- `owner_input`;
- `repository_curation`;
- `no_op`.

Every operation names its write class, target, before hash, candidate after
hash, reason, validator and rollback behavior.

`candidate after hash` means the deterministic semantic hash. A separate
physical result hash is computed after audit-only values are rendered during
apply. The plan schema names both fields explicitly to avoid treating them as
interchangeable.

## Plan Fingerprint

The fingerprint is computed from canonical compact JSON containing:

- source workspace schema state;
- target version;
- ordered migration ids and versions;
- ordered operation descriptors;
- before hashes and missing-state markers;
- normalized owner inputs;
- policy and planner versions.

It excludes timestamps, absolute paths, filesystem enumeration order and
presentation-only text.

Candidate renderers receive a deterministic semantic audit placeholder while
planning. Apply substitutes one transaction-wide audit timestamp only after the
semantic fingerprint matches. The result reports both the reviewed semantic
hash and final physical file hash.

Apply recomputes the plan from current sources and compares fingerprints. A
mismatch returns `stale_plan` with no writes.

## Transaction Lifecycle

### Preflight

1. Reject an existing interrupted transaction.
2. Reject a lower target and resolve the adjacent forward migration path.
3. Verify transition/runtime inspect, plan and apply support.
4. Resolve actor authority and explicit confirmation.
5. Recompute and compare the semantic plan fingerprint.
6. Validate path ownership and reject escapes/symlink traversal.
7. Confirm all required owner inputs are present.
8. Acquire the exclusive workspace migration lock.
9. Recompute source/target preconditions under the lock.

### Stage

1. Create a transaction directory under a declared internal migration temp
   root on the same filesystem as `.p2p`, with mode `0700` where supported.
2. Record the plan, original hashes and intended target order in a redacted
   journal and sync the journal plus containing directory.
3. Snapshot original bytes and absence markers for every target.
4. Render all candidate files into the transaction overlay.
5. Validate each candidate artifact through its owner service.
6. Validate the complete overlay through `CandidateWorkspaceView` and prove
   migration-owned reads resolve to candidate bytes.

### Commit

1. Recheck each target preimage immediately before its replacement and replace
   non-schema targets in deterministic path order, syncing replaced files and
   parent directories where supported.
2. Revalidate committed canonical state required by the transition.
3. Replace `workspace-schema.yml` last.
4. Record final physical hashes and mark the journal committed.
5. Remove transaction scratch and release the migration lock.

### Failure And Recovery

- Before replacement: remove scratch and return `blocked` or `stage_failed`.
- During replacement: restore original files in reverse replacement order.
- Complete rollback: return `rolled_back` and remove scratch.
- Incomplete rollback/crash: retain journal and snapshots, return/detect
  `recovery_required`, and block new apply operations.
- Explicit recovery supports `status`, `rollback` and, only if all current hashes
  match journal expectations, `resume`.

No result may report success while a transaction journal remains unresolved.
No success, no-op or complete rollback result may leave the exclusive lock or
transaction root discoverable as active state. Transaction paths are excluded
from compatibility inventory, registries, freshness collectors and ordinary
validation except the dedicated recovery inspector.

Rollback restores a target only when its current hash is the exact candidate
hash written by the transaction. A different hash is treated as an external
concurrent edit: rollback stops for that target, retains recovery evidence and
does not overwrite the edit silently.

### Internal Transaction Layout

The code-owned transient layout is:

```text
.p2p/.internal/workspace-migrations/
  apply.lock
  transactions/<transaction-id>/
    journal.yml
    originals/
    candidates/
```

The lock is acquired with an exclusive create primitive before its diagnostic
payload is written. The directory and transaction children use mode `0700`
where supported. A stale-looking pid never authorizes automatic lock stealing:
recovery status explains whether explicit rollback/resume/cleanup is available.
Only the recovery inspector reads this root as state; all other inventory treats
it as declared transient internal storage.

### Runtime Contract Alignment Reuse

The release may change the engine version while this repository is pinned to an
exact older version. Runtime-contract preview/update remains a distinct owner
operation and runs before workspace planning. Its setup-guide and contract
writes reuse the multi-file transaction helper. If platform or legacy behavior
cannot do so, M1 remains blocked until the service demonstrates and documents a
complete recovery from its explicit partial-failure result.

## Registered Migration: Legacy Undeclared To V1

The first migration is a composite transition whose plan may contain:

1. workspace schema state adoption;
2. decision parser/alias compatibility prerequisite check;
3. explicit vertical selection input;
4. active vertical, lock and initial definition candidate rendering;
5. rubric convergence;
6. domain state materialization;
7. permission state materialization;
8. owner-provided project metadata patch;
9. coverage and relation curation actions reported but not auto-applied;
10. derived refresh actions deferred until canonical commit.

The transition can apply a safe subset only if omitted work is explicitly
classified as non-blocking degraded compatibility. It cannot mark the workspace
fully current while required migration operations remain unresolved.

## Vertical And Rubric Migration

The migration planner builds a candidate from:

- selected resolvable vertical;
- selected profile and modules;
- existing domain and rubric state;
- stable criterion-id matches;
- explicit owner mapping for semantic collisions.

Rules:

- lock checksum is computed before staging output;
- definition sections start from the vertical contract;
- proposal keyword matches may be attached as suggestions only;
- stable matching rubric ids retain enabled state;
- legacy criteria with no semantic match remain visible as
  `legacy_unmapped` and do not count toward vertical baseline coverage;
- no criterion is deleted without a separate explicit operation;
- the staged active state, lock, definition and rubrics validate as one unit.

Ordinary explicit vertical selection uses the same complete candidate renderer
and validator. Project-definition changes expose a pure preview returning the
current source hash, normalized operations, semantic diff, resulting definition
hash and preview token. Repository migration uses a stale-preview-protected
apply path; the existing update command remains source compatible by delegating
to the same patch engine.

## Domain, Permission And Metadata Migration

Domain candidate:

- use a valid `.p2p/project.yml` project domain when present;
- otherwise require owner input;
- write explicit provenance and current domain contract shape.

Permission candidate:

- inspect explicit permissions first;
- otherwise inspect valid legacy governance roles;
- require one explicit owner identity;
- preserve repository mode and supported legacy roles;
- block conflicting owner resolution.

Metadata candidate:

- use a narrow patch schema for project status, workflow phase, current goal and
  other explicitly allowed fields;
- preserve project id, remote and repository configuration by default;
- never infer that `bootstrap_manual` is obsolete without owner input.

Metadata preview returns only allowed changed fields, current/candidate hashes,
authority requirements and a stale-preview token. Apply requires actor,
confirmation and the matching token. Runtime, remote and repository fields are
not writable through this primitive.

## Decision-Context Compatibility

### Decision State Resolution

1. Parse recognized lifecycle token from `Status` when available.
2. Otherwise accept a recognized lifecycle token from `Outcome` for legacy
   formats that used Outcome as state.
3. Preserve non-state Outcome text as decision statement content.
4. Emit unknown-state diagnostics only when no recognized token exists.

### Conflict Collections

Normalize `winner` and `rejected` through shared scalar-or-sequence helpers.
Each rejected proposal becomes its own supersession assertion with direct
evidence.

### Relation Policy

The versioned alias table classifies terms as:

- exact canonical relation;
- unambiguous compatibility alias;
- ambiguous term requiring curation;
- invalid/unknown term.

Aliases such as a simple `dependency` can map to `depends_on` after tests prove
direction. Terms such as `enables`, `informs` and `constrained_by` require an
explicit direction/semantic decision before the policy claims support.

### Supported Semantic Correction Writes

Impact correction operates on the complete supplied impact artifact set. It
parses and validates all artifacts, computes a per-target diff and one preview
token before writing. Apply rechecks source hashes and commits the set through
the transaction helper, so one invalid artifact or failed replacement changes
none of the targets.

Conflict correction addresses one stable conflict id. Preview validates type,
proposal ids, winner/rejected consistency, reason and provenance. Apply updates
that record atomically with actor and confirmation. Appending a second
contradictory conflict is not a correction strategy.

Authority is resolved through existing permission/governance services. Replacing
semantic artifacts on a committed-authority proposal or changing project
conflict memory requires the owner or an explicitly authorized actor; transport
defaults such as `actor=owner` are never sufficient evidence by themselves.

## Vertical-Coverage Surface

Proposed CLI:

```text
p2p proposal vertical-coverage show PROP-XXX --format json
p2p proposal vertical-coverage suggest PROP-XXX --format json
p2p proposal vertical-coverage preview PROP-XXX coverage.yml --format json
p2p proposal vertical-coverage import PROP-XXX coverage.yml \
  --preview-token TOKEN --confirm --actor ACTOR
```

`suggest` is read-only. `import` validates a complete replacement artifact and
writes the coverage artifact and artifact-state provenance atomically through
the proposal artifact service. A future narrow `set` command may wrap import but
must not become arbitrary YAML editing.

Suggestion uses token/phrase boundaries, section-specific terms, source type,
rare-term weighting and explicit confidence thresholds. Generic terms that
match most proposals are downweighted or suppressed. Suggested evidence remains
separate from declared coverage even at high confidence.

Schema v1 remains readable. New writes add optional provenance:

```yaml
vertical_coverage:
  schema_version: 1
  proposal_id: PROP-100
  vertical_id: software_project
  sections:
    - id: data_model
      relevance: direct
      rationale: Defines decision context entities and relations.
      source: declared
  provenance:
    actor: owner
    authority: owner_confirmed
    migrated_from: ""
```

## Progress Model

The first public model contains separate axes.

### Definition Completeness

- required sections complete/applicable sections;
- required fields populated/required fields;
- blocked sections;
- assumptions by state;
- open questions;
- explicit exclusions and not-applicable sections.

Fieldless required sections use explicit section status. A missing definition
returns `not_initialized` and no percentage.

### Evidence Coverage

- required sections with accepted declared proposal coverage;
- sections with only draft/historical declared coverage;
- sections with heuristic suggestions only;
- unmapped proposals as informational context, not denominator inflation.

Every ratio includes counts and policy version. No aggregate overall percentage
is emitted in v1.

Proposed CLI:

```text
p2p project progress
p2p project progress --format json
```

Existing assessment and maturity commands remain compatible but gain additive
basis/freshness warnings where required.

## Derived Freshness Graph

Initial dependency order:

```text
canonical project/proposal/decision/change/choice/work state
  -> registries
  -> rationalized project state and feature projections
  -> decision-context snapshot/manifest when materialized
  -> assessment, maturity and project progress snapshots
  -> operational brief context/prompt
  -> operational brief and managed next actions [agent/owner stage]
  -> software-spec exports [per Change Set]
  -> visible project export
  -> publication packet
  -> curated publication, validation and render
  -> owner review/approval
```

The graph distinguishes deterministic service actions from agent/owner stages.
Freshness status never marks a downstream stage current merely because its file
exists.

Project feature projections use the shared lifecycle-authority policy. The
initial repository count is therefore 94 committed-authority proposals: 93
`accepted` and one `accepted_with_changes`, not an exact-string count of 93.
Refresh records an owned-output manifest, creates the expected set and removes
only obsolete owned projection paths. Unknown and manually owned paths are
reported and preserved.

Operational brief, next actions and software-spec nodes are not all automatic:
the graph records source fingerprints, current status and the next supported
command while respecting their agent/owner lifecycle.

Proposed CLI:

```text
p2p project freshness
p2p project freshness --format json
p2p project freshness refresh-deterministic --confirm
```

The refresh command is optional for the first implementation if ordered status
and existing suggested commands are complete. It must not curate, review or
approve publication.

## CLI Surface

Proposed additive command groups:

```text
p2p workspace schema status [--format text|json]
p2p workspace migrate plan [--to VERSION] [--input PATCH] [--format text|json]
p2p workspace migrate apply --to VERSION --input PATCH \
  --plan-fingerprint HASH --confirm --actor ACTOR
p2p workspace migrate recovery status [--format text|json]
p2p workspace migrate recovery rollback --confirm --actor ACTOR
p2p workspace migrate recovery resume --confirm --actor ACTOR
p2p project definition preview PATCH --format text|json
p2p project definition apply PATCH --preview-token TOKEN --confirm --actor ACTOR
p2p impact preview PROP-XXX SOURCE --format text|json
p2p impact apply PROP-XXX SOURCE --preview-token TOKEN --confirm --actor ACTOR
p2p conflict preview-update CONFLICT-ID PATCH --format text|json
p2p conflict update CONFLICT-ID PATCH --preview-token TOKEN --confirm --actor ACTOR
```

Existing `impact import` remains available for backward-compatible import
workflows, but is refactored to validate the complete input set before an atomic
commit. Corrections to existing artifacts on committed-authority proposals use
the preview/apply path. Existing project-definition update parsing remains
compatible and delegates to the same pure patch renderer; M2 uses preview/apply.

Exit behavior:

- status/plan return nonzero only for invalid/unsupported state, not ordinary
  degraded legacy state;
- apply returns nonzero for blocked, stale-plan, stage-failed, rolled-back or
  recovery-required results;
- JSON is emitted without Rich formatting;
- apply output lists every changed/restored path and final schema state.

`p2p doctor`, `p2p status`, compact context and generated next actions expose an
additive schema/migration summary. An interrupted transaction takes precedence
over ordinary migration suggestions and names the exact recovery commands.

## MCP Surface

After CLI/service stabilization, add read-only tools equivalent to:

- workspace schema status;
- migration plan;
- project progress;
- derived freshness;
- vertical-coverage show/suggest.

Migration apply and recovery remain CLI-only in v1. Vertical-coverage import may
reuse an existing write-safe artifact import boundary only when the tool schema
can restrict the exact target and validate the payload.

## Validation Integration

Global validation gains additive findings for:

- missing/invalid/ahead workspace schema state;
- interrupted migration transaction;
- software-domain project using fallback vertical;
- active vertical without coherent lock/definition set;
- explicit permissions/domain state missing where current schema requires it;
- stale legacy rubrics not mapped to active vertical;
- malformed vertical coverage and related-proposal contracts;
- derived-state divergence as warning/advisory, not canonical corruption.

Legacy fallback remains operable during planning. Validation must not claim a
fully current workspace merely because all files that happen to exist parse.

## Release And Documentation Gate

Before repository dogfooding, source package version, project metadata, MCP
server version, changelog and migration documentation must describe one release.
Generated agent instructions must expose schema status, no-write planning and
recovery commands while retaining the prohibition on manual `.p2p` repair.

An exact-pinned workspace is expected to become runtime-incompatible after a
release bump until its owner updates the runtime contract. That state is not a
workspace-schema failure. M1 records and resolves the runtime contract first,
then computes a fresh workspace migration fingerprint.

## Repository Dogfooding Flow

### M1 - Baseline And Dry Run

Capture status, schema plan, vertical context, definition, rubrics, permissions,
project metadata, proposal artifact distribution, decision-index diagnostics,
derived counts, assessment/maturity and publication freshness. Obtain owner
inputs and freeze the reviewed plan fingerprint. Evidence is stored at
`specs/features/workspace-schema-versioning-and-legacy-migration/implementation.md`.
If the implementation release no longer satisfies the repository's exact
runtime contract, preview and owner-apply the runtime contract update first,
then regenerate the workspace plan and fingerprint.

### M2 - Project Definition

Apply generic schema/vertical/domain/permission migration. Then use structured
definition patches in small section groups. Each patch records evidence source
and leaves uncertain fields missing/assumed/blocked. Preview/diff and owner
confirmation precede every batch apply.

### M3 - Historical Relations

Rebuild the index after F6. Curate only remaining diagnostics caused by source
semantics. Use supported proposal impact/relation import and conflict commands;
do not edit artifact files directly. Each bounded batch uses one reviewed
preview token and is followed by index/diagnostic comparison.

### M4 - Selective Coverage

Start with foundational proposals, active work and recent vertical/runtime/
decision-memory proposals. Review suggestions and import approved mappings.
Record the unreviewed remainder as legacy/unmapped. Coverage plus artifact-state
provenance commit atomically.

### M5 - Rebuild

Refresh deterministic derived layers in graph order, rerun progress and index
diagnostics, reconcile owned project projections, prepare publication outputs,
and compare every freshness node with M1. Verify runtime compatibility and no
active lock/scratch. Owner review and publication approval remain separate.

## Testing Strategy

### Unit And Contract Tests

- schema state parsing and serialization;
- migration graph path resolution;
- plan identity and fingerprint determinism;
- forward-only and transition/runtime capability resolution;
- semantic versus physical hash behavior across different apply dates;
- lock ownership and stale-lock/recovery state;
- decision lifecycle and relation alias policy;
- progress ratio arithmetic;
- freshness graph ordering and cycle rejection.

### Service Tests

- missing/current/ahead/invalid schema states;
- no-write compatibility planning;
- owner-input blockers;
- full stage validation;
- candidate-overlay read routing;
- injected write failure at every commit position;
- two-process concurrent apply and durable journal/directory sync behavior;
- complete and incomplete rollback;
- interrupted recovery status/resume/rollback;
- vertical/domain/permission candidate generation;
- coverage suggestion/import;
- definition, impact and conflict preview/apply stale-token behavior;
- lifecycle-aware projection reconciliation and owned-output cleanup;
- mixed derived freshness.

### Public Contract Tests

- CLI text and JSON parity;
- exit codes for degraded, blocked, stale-plan and recovery states;
- no MCP apply tool;
- read-only MCP parity where added;
- existing runtime, vertical, validation, proposal and project commands remain
  backward compatible.

### Migration Fixtures

- fresh current workspace;
- minimal legacy workspace;
- this repository's structural shape without repository content;
- active vertical without lock;
- domain/rubrics without vertical;
- missing permissions with valid legacy roles;
- ambiguous owner identity;
- malformed schema state;
- ahead-of-runtime schema;
- runtime able to inspect but not apply a transition;
- downgrade request;
- interrupted transaction;
- concurrent apply and stale lock;
- historical decision formats and relation vocabularies;
- stale mixed derived state;
- 100-proposal scale fixture.

### Verification Gates

Each `F*` slice runs focused tests plus all earlier migration regressions. Before
M1, run the full suite. M5 requires full tests, runtime status, validation,
schema status, progress, decision-index diagnostics and freshness review.

## Risks And Mitigations

- Risk: schema version becomes another stale marker.
  Mitigation: validation derives compatibility independently and verifies applied
  migration history against registered transitions.
- Risk: multi-file apply fails after partial replacement.
  Mitigation: staged overlay, journal, original bytes, reverse rollback and
  explicit recovery.
- Risk: concurrent writers invalidate source hashes between preflight and commit.
  Mitigation: exclusive process-safe lock and precondition checks under lock.
- Risk: validators accidentally inspect live files instead of staged candidates.
  Mitigation: candidate workspace view with instrumented read-routing tests.
- Risk: audit timestamps make reviewed plans unreproducible.
  Mitigation: semantic plan hashes and separately reported physical result hashes.
- Risk: automatic semantic migration changes project meaning.
  Mitigation: typed owner inputs and repository-curation operations block apply.
- Risk: rubric preservation keeps misleading scores.
  Mitigation: separate active baseline from visible legacy-unmapped criteria.
- Risk: heuristic coverage becomes authority.
  Mitigation: suggestion and declared import remain separate contracts.
- Risk: derived refresh deletes unknown user material or ignores committed
  lifecycle states.
  Mitigation: shared authority policy and exact owned-output manifest with
  preserve-by-default behavior.
- Risk: feature becomes one unreviewable implementation.
  Mitigation: strict `F*` gates, independently releasable slices and no M work
  before engine gates pass.

## Out Of Scope Follow-Ups

- Remote/server workspace migrations.
- Persistent migration service or queue.
- Automatic cross-repository fleet upgrades.
- Database-backed decision-context cache migration.
- MCP migration apply.
- A UI for migration plans and owner-input review.
