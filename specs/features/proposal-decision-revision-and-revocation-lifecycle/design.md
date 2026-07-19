# Design - Proposal Decision Revision And Revocation Lifecycle

## Requirements Covered

- F1: R-F1-001..022.
- F2: R-F2-001..022.
- F3: R-F3-001..023.
- F4: R-F4-001..014.
- F5: R-F5-001..023.
- F6: R-F6-001..019.
- F7: R-F7-001..012.
- F8: R-F8-001..017.
- F9: R-F9-001..014.
- Cross-cutting: N001..020, E001..030 and AC001..030.

## Design Goals

- Make proposal decision history canonical, queryable and tamper-evident.
- Preserve current Markdown usability without allowing projections to compete
  with structured authority.
- Make invalid transitions impossible before any write.
- Keep owner decisions explicit across local CLI and delegated MCP execution.
- Reuse existing preview, permission, operation-gate, transaction and migration
  infrastructure.
- Prevent revocation from pretending that dependent implementation was
  automatically reversed.
- Keep schema-v2 projects readable while making schema-v3 writes unambiguous.
- Give every existing consumer one lifecycle-authority result instead of
  duplicating status policy.
- Establish stable event-head and authority-interval bindings for future
  decision-memory consolidation.

## Key Decisions

- D001: Workspace schema v3 introduces proposal decision ledgers.
  Rationale: the canonical authority model changes, so a silent additive file
  in schema v2 would allow old and new runtimes to write conflicting truths.

- D002: The canonical artifact is
  `.p2p/proposals/<proposal-dir>/decision-events.yml`.
  Rationale: it is proposal-local, discoverable, structured and distinct from
  the human `decision.md` projection.

- D003: Each proposal owns one ledger containing an ordered event chain.
  Rationale: one ledger gives one head, one integrity boundary and one
  deterministic lifecycle without cross-file append races.

- D004: `proposal.md` and `decision.md` remain engine-owned projections.
  Rationale: they are established human and compatibility surfaces, but cannot
  remain independent authority sources.

- D005: An ambiguous legacy proposal has no fabricated decision event.
  Rationale: unusable legacy values are evidence, not owner decisions. Its
  ledger has `authority_resolution=unknown_legacy`, an empty event chain and
  preserved `legacy_evidence`.

- D006: Owner curation of unknown legacy authority creates the first current
  event at the curation date.
  Rationale: it records a real owner decision now without inventing a historical
  event date or active interval.

- D007: Event identity is content-addressed and operation-key-bound.
  Rationale: the same semantic request can be recognized after response loss,
  while a reused operation key with different input is rejected.

- D008: Proposal and decision fingerprints are separate.
  Rationale: proposal content drift must block stale apply and changed
  reinstatement, while revocation needs to reference the exact accepted
  decision semantics.

- D009: Reinstatement has event type `reinstated` but effective state equal to
  the referenced active outcome.
  Rationale: current authority becomes active again without erasing the
  revocation/reinstatement history.

- D010: All authority-changing events use one stateless preview/apply service.
  Rationale: separate accept, reject and revoke writers would recreate
  transition and retry drift.

- D011: CLI apply requires a current owner actor; MCP apply may be executed by
  another declared actor only with consent approved by the current owner and
  bound to the preview token.
  Rationale: execution delegation must not be confused with decision authority.

- D012: The mutation transaction normally writes three proposal-local targets:
  ledger, proposal status projection and decision projection. Accepted requests
  with an explicit readiness override add `readiness.yml` to the same atomic
  candidate.
  Rationale: dependent lifecycles and derived state have separate ownership,
  while a readiness override attached to acceptance must not become orphaned.

- D013: Impact capture is complete internally and bounded only at rendering.
  Rationale: a display limit cannot make a revocation token ignore hidden
  dependencies.

- D014: Remediation next actions are generated, not persisted by decision apply.
  Rationale: they can be deterministically recomputed from the event head and
  current dependencies without mixing a decision transaction with curated
  project actions.

- D015: Schema-v3 reads fail closed on a missing or invalid ledger.
  Rationale: falling back to apparently valid projections would reintroduce
  overwrite authority.

- D016: Schema-v2 reads use an explicit legacy adapter.
  Rationale: compatibility behavior remains visible, testable and removable in
  a future major line.

- D017: Consumer migration is enforced by dependency injection and tests that
  mutate projection text independently from the ledger.
  Rationale: code search alone cannot prove that direct status parsing has
  disappeared.

- D018: Existing one-step decision commands remain as named compatibility
  entry points but may only preview or apply through the new contract.
  Rationale: preserving unsafe immediate writes is not backward compatibility;
  it is a governance bypass.

- D019: The v2-to-v3 migration normalizes both projections after preserving all
  usable original values in the ledger.
  Rationale: a schema-v3 workspace must not start with known projection drift.

- D020: Ledger repair never truncates or rewrites a validated prefix.
  Rationale: automatic history destruction would defeat the feature's primary
  purpose.

- D021: A decision event binds proposal semantics; later body drift does not
  revoke the event but makes current proposal claims unusable as accepted
  authority.
  Rationale: direct or accidental edits must neither rewrite governance history
  nor smuggle changed intent under an old acceptance.

## Current-System Constraints

- `core/decision.py` currently models one outcome and one decision value.
- `services/proposal_decisions.py` owns an overwrite-only write path with direct
  `Path.write_text()` calls.
- `services/proposals.py` creates `decision.md` and reads both projections
  directly.
- `services/lifecycle_authority.py` is a token policy, not a workspace-aware
  authority reader.
- `services/decision_context_authority.py` has a separate lifecycle map.
- `services/changes.py` checks for exact `accepted` status and stores only a
  `decision.md` path.
- `services/software_spec_lifecycle.py` requires exact `accepted`.
- `services/validation.py` compares two projection values.
- `services/registry_records.py`, project services, exports and freshness contain
  direct proposal/decision reads.
- `services/decision_context_sources.py` currently catalogs `decision.md` as
  canonical semantic input.
- `AtomicMutationWriter` already supports multi-target source preconditions,
  candidate validation, rollback and recovery-required output.
- `WorkspaceMigrationRegistry` requires adjacent transitions and already
  composes candidates through handlers.
- `WorkspaceOperationCompatibilityService` fails unknown write operation IDs
  closed and distinguishes schema-v1-safe and schema-v2-only operations.
- `PermissionsService` resolves declared actors and can require owner role.
- MCP consent receipts already bind operation, target and actor, but decision
  apply needs an additional preview-token-bound target convention.

## Proposed Module Boundaries

### Core Models

Add `src/p2p_engine/core/proposal_decision_events.py` with immutable types and
enums only:

- `ProposalDecisionEventType`
- `ProposalDecisionEffectiveState`
- `ProposalDecisionAuthorityResolution`
- `ProposalDecisionLineageKind`
- `ProposalDecisionCondition`
- `ProposalDecisionAuthorityEvidence`
- `ProposalDecisionLineage`
- `ProposalDecisionImpactBinding`
- `ProposalDecisionMigrationProvenance`
- `ProposalDecisionLegacyEvidence`
- `ProposalDecisionEvent`
- `ProposalDecisionLedger`
- `ProposalDecisionAuthorityInterval`
- `ProposalDecisionLifecycleView`
- `ProposalDecisionRequest`
- `ProposalDecisionPreview`
- `ProposalDecisionApplyResult`
- `ProposalDecisionImpact`
- `ProposalDecisionImpactItem`
- `ProposalDecisionHistoryPage`
- repair and legacy-resolution request/result types.

Core types do not read files, resolve permissions or call services.

### Ledger Codec And Integrity

Add `services/proposal_decision_ledger.py`:

- strict YAML parsing and duplicate-key rejection;
- semantic normalization and serialization;
- proposal and decision fingerprint calculation;
- event ID and event hash calculation;
- predecessor-chain and head validation;
- empty-ledger rendering;
- v3 projection rendering;
- candidate repair validation;
- repository-relative source descriptors.

The codec accepts bytes and returns typed results. It does not discover proposal
directories or write files.

### Lifecycle Authority

Evolve `services/lifecycle_authority.py` into two layers:

1. pure versioned policy functions for transition and authority classification;
2. `ProposalLifecycleAuthorityService`, which reads one proposal snapshot and
   returns `ProposalDecisionLifecycleView`.

The old token helpers remain narrow compatibility wrappers for already-captured
status values. Workspace consumers receive the service result and do not call
those wrappers on independently parsed Markdown.

### Decision Application

Replace the internals of `ProposalDecisionService` with:

- `status(proposal_id)`
- `history(proposal_id, limit, cursor)`
- `preview(request, execution_context)`
- `apply(request, preview_token, confirm, execution_context)`
- `projection_repair_preview/apply`
- `ledger_repair_preview/apply`
- `legacy_resolution_preview/apply`.

It coordinates ledger codec, lifecycle policy, permissions, impact capture,
mutation preview and `AtomicMutationWriter`. It remains unaware of Typer and MCP
wire shapes.

### Impact Service

Add `services/proposal_decision_impact.py`:

- captures dependency sources once;
- builds direct and transitive dependency indexes;
- classifies affected lifecycle objects;
- returns a complete typed impact snapshot and bounded pages;
- computes an impact semantic fingerprint;
- exposes generated remediation action candidates.

It reads through existing Change, Work, spec, vertical, project, context,
freshness and publication services or captured registries. It performs no
writes.

### Legacy Adapter

Add `services/proposal_decision_legacy.py`:

- captures schema-v2 `proposal.md` and `decision.md` once;
- resolves only supported aligned values;
- returns explicit divergence/malformed diagnostics;
- never derives owner/date/rationale from external metadata;
- renders v2-to-v3 ledger and projection candidates.

This is the only schema-v2 decision authority adapter.

### Migration Handler

Add `WorkspaceV2ToV3ProposalDecisionLedgerHandler` to
`workspace_migration_handlers.py` and register it after v1-to-v2.

Owned candidate targets:

```text
.p2p/proposals/*/decision-events.yml
.p2p/proposals/*/proposal.md
.p2p/proposals/*/decision.md
.p2p/project/workspace-schema.yml
```

The managed prefix is narrowed by candidate validation to existing valid
proposal directories and those three exact filenames. The handler cannot own
other proposal artifacts.

Validators:

- `ProposalDecisionLedgerService`
- `ProposalLifecycleAuthorityService`
- proposal projection validator
- `WorkspaceSchemaService`
- global candidate workspace validation.

### Presentation And Adapters

- `cli_commands/proposal_decisions.py` parses and renders only.
- A dedicated MCP decision catalog/handler module may be extracted if the
  existing proposal module becomes too broad.
- `P2PWorkspace` constructs services and delegates methods.
- Registry, project, Change, Work, spec, context and export services receive a
  lifecycle-view callable or captured lifecycle map.

## Ledger Contract

### Path And Root

```text
.p2p/proposals/PROP-102-.../decision-events.yml
```

```yaml
proposal_decision_ledger:
  contract_version: 1
  proposal_id: PROP-102
  authority_resolution: resolved
  effective_state: accepted
  head_event_id: PDE-0123456789abcdef01234567
  events: []
  legacy_evidence: []
```

The root keys are closed for contract version 1. Optional fields are represented
by omission or explicit empty collections according to one serializer policy;
the serializer does not alternate forms.

### Event Shape

```yaml
- event_schema_version: 1
  event_id: PDE-0123456789abcdef01234567
  operation_key: P2POP-0123456789abcdef01234567
  proposal_id: PROP-102
  event_type: accepted
  effective_state: accepted
  rationale: The proposal is ready.
  conditions: []
  decided_on: "2026-07-17"
  authority:
    owner_id: mrjungle
    owner_role: owner
    executor_actor_id: mrjungle
    executor_kind: person
    channel: cli
    permission_policy_sha256: "<64 hex>"
    consent_id: null
    consent_sha256: null
  predecessor:
    event_id: null
    event_sha256: null
  proposal_semantic_sha256: "<64 hex>"
  decision_semantic_sha256: "<64 hex>"
  affected_decision:
    event_id: null
    decision_semantic_sha256: null
  lineage:
    kind: null
    targets: []
  impact:
    required: false
    preview_token: null
    source_fingerprint_sha256: null
    total_count: 0
  readiness:
    source_fingerprint_sha256: null
    owner_override: false
  mutation:
    preview_token: "<64 hex>"
    request_fingerprint_sha256: "<64 hex>"
  migration: null
  event_sha256: "<64 hex>"
```

YAML output may omit null-only optional mappings if the parser normalizes them
to the same typed value. Tests freeze one canonical serialization.

### Empty And Unknown Legacy Ledgers

A fresh undecided ledger:

```yaml
authority_resolution: resolved
effective_state: undecided
head_event_id: null
events: []
legacy_evidence: []
```

An ambiguous migrated ledger:

```yaml
authority_resolution: unknown_legacy
effective_state: unknown_legacy
head_event_id: null
events: []
legacy_evidence:
  - migration_id: workspace-v2-to-v3
    source_paths:
      - .p2p/proposals/PROP-001-.../proposal.md
      - .p2p/proposals/PROP-001-.../decision.md
    source_sha256:
      proposal.md: "<64 hex>"
      decision.md: "<64 hex>"
    values:
      proposal_status: accepted
      decision_status: rejected
      outcome: rejected
      reason: Original readable value
      approver: unknown_legacy
      decided_on: unknown_legacy
    diagnostics:
      - P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED
```

Readable malformed values are bounded and preserved exactly as scalar evidence.
Binary or oversized input is represented by source digest, size and diagnostic,
not copied without limit into YAML.

### Input Limits

Contract-version-1 limits are measured on UTF-8 bytes after newline
normalization and before event identity calculation:

- rationale: 1 byte minimum, 64 KiB maximum;
- one condition text: 1 byte minimum, 8 KiB maximum;
- conditions: 64 maximum and 64 KiB combined;
- lineage targets: 100 maximum;
- one preserved legacy scalar: 4 KiB maximum inline, with full digest, original
  byte count and explicit truncation marker beyond that;
- one ledger or reviewed repair candidate: 32 MiB maximum;
- impact presentation limit: default 20, maximum 100, while the complete
  internal fingerprint remains unbounded by presentation.

NUL and unsupported control characters are rejected. Limit diagnostics report
the measured and allowed values without echoing oversized content.

## Identity And Fingerprints

### Canonical Encoding

Use `canonical_json_bytes()` and `semantic_sha256()` from the existing mutation
preview contract. Every policy payload includes its policy version.

### Proposal Semantic Fingerprint

Input:

```text
proposal_semantics_policy_version
proposal_id
title
Problem
Context
Goals
Non-Goals
Proposal
Acceptance Criteria
material accepted conditions when event type is accepted_with_changes
```

Excluded:

- `Status`
- projection `Decision`
- file path outside repository-relative identity
- mtimes and audit timestamps
- readiness score and derived artifacts.

Markdown parsing uses the established section parser and explicit list
normalization. Duplicate semantic sections are invalid for decision apply.

### Decision Semantic Fingerprint

For `accepted` and `accepted_with_changes`:

```text
decision_semantics_policy_version
proposal_semantic_sha256
active outcome
normalized rationale/qualifiers
ordered structured conditions with stable condition IDs
```

For revocation/replacement events, `affected_decision` references that value.
For reinstatement, the candidate active fingerprint must equal the referenced
prior active event exactly; the reinstatement event receives its own event hash
but does not create a changed decision fingerprint.

### Operation And Event Identity

- Preview accepts an optional explicit operation key.
- If omitted, the service creates and returns a random-independent,
  content-addressed `P2POP-<24 hex>` from request semantics and source head.
- Apply must receive the operation key returned by preview.
- `event_id` is `PDE-<24 hex>` from:
  - operation key;
  - proposal ID;
  - event type/effective state;
  - decision date;
  - authority semantic evidence;
  - predecessor event/hash;
  - proposal/decision/impact fingerprints;
  - lineage;
  - structured conditions;
  - migration provenance.
- `event_sha256` hashes the canonical full event excluding only
  `event_sha256`.
- Full 64-character digests are retained in fields used for collision
  validation. Prefix collisions fail rather than selecting a new identity by
  enumeration order.
- Event dates are parsed as canonical ISO dates and are non-decreasing across
  predecessor order. Equal dates are valid; backdated successors are not.

## Lifecycle And Authority

### Effective States

```text
undecided
accepted
accepted_with_changes
deferred
withdrawn
rejected
revoked
superseded
split
merged_into_other
unknown_legacy
```

`reinstated` is an event type, not a stored effective state. Its effective state
is restored from the referenced prior active event.

### Transition Matrix

`retry` below means exact operation replay only.

| Current state | accepted | accepted_with_changes | deferred | withdrawn | rejected | revoked | superseded | split | merged_into_other | reinstated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| undecided | allow | allow | allow | allow | allow | deny | deny | allow | allow | deny |
| deferred | allow | allow | retry | allow | allow | deny | deny | allow | allow | deny |
| accepted | retry | deny | deny | deny | deny | allow | allow | allow | allow | deny |
| accepted_with_changes | deny | retry | deny | deny | deny | allow | allow | allow | allow | deny |
| revoked | deny | deny | deny | deny | deny | retry | deny | deny | deny | allow exact |
| withdrawn | deny | deny | deny | retry | deny | deny | deny | deny | deny | deny |
| rejected | deny | deny | deny | deny | retry | deny | deny | deny | deny | deny |
| superseded | deny | deny | deny | deny | deny | deny | retry | deny | deny | deny |
| split | deny | deny | deny | deny | deny | deny | deny | retry | deny | deny |
| merged_into_other | deny | deny | deny | deny | deny | deny | deny | deny | retry | deny |
| unknown_legacy | deny | deny | deny | deny | deny | deny | deny | deny | deny | deny |

For terminal rows, only the exact previously committed operation can return
`already_applied`. A new operation requesting the same event is not a second
event and returns an already-effective diagnostic rather than extending
history.

`unknown_legacy` exits only through the separate owner legacy-resolution
primitive, which creates the first event under an explicit recovery mode.

### Required Fields

| Event | Required additional input |
| --- | --- |
| accepted | no lineage; impact optional |
| accepted_with_changes | at least one structured non-empty condition with stable ID |
| deferred | reason |
| withdrawn | reason |
| rejected | reason |
| revoked | affected active event and complete impact binding |
| superseded | affected active event, one replacement target, complete impact binding |
| split | at least two split targets, complete impact binding; affected active event only when currently active |
| merged_into_other | one merge target, complete impact binding; affected active event only when currently active |
| reinstated | revocation event, referenced prior active event, complete impact binding |

### Authority Intervals

The lifecycle view derives intervals rather than storing a mutable interval
list:

- accepted/accepted-with-changes opens an interval at its event ID/date;
- revoked/superseded/split/merge closes the current interval at its event
  ID/date;
- reinstated opens a new interval referencing the restored event fingerprint;
- rejected/withdrawn/deferred never open an interval;
- unknown legacy authority has no fabricated interval.

The view exposes `ever_active`, current `active`, prior intervals and an
`interval_precision` field (`event_date` or `unknown_legacy`).

It also exposes `proposal_binding_status`:

- `current`: current normalized proposal semantics match the controlling
  event;
- `diverged`: current bytes are readable but semantics differ;
- `unavailable`: current proposal semantics cannot be parsed safely.

The event remains the authority history in all three cases. Consumers that need
accepted proposal claims require `current`; they do not reinterpret divergence
as revocation.

### Proposal Update Policy

`ProposalDocumentService.update()` receives the lifecycle view:

- undecided/deferred: semantic edits are permitted and the next decision binds
  the new fingerprint;
- active or terminal state: render the candidate first and allow only a
  normalization-equivalent semantic fingerprint;
- changed active/terminal intent: block with a command to create a linked
  proposal;
- direct/manual drift: validation reports it and derived consumers requiring
  current claims block.

An owner may still retire affected active authority through revoke,
supersede, split or merge after explicitly acknowledging the drift. The event
targets the stored active decision fingerprint and the preview binds the
current divergent proposal bytes. Acceptance and reinstatement cannot use a
diverged binding.

### Lineage Validation

Validation uses one request-scoped proposal identity/lifecycle map:

- no self-target;
- no duplicate target;
- target must exist;
- replacement/merge target must be distinct and not terminally incompatible;
- split has at least two targets;
- reciprocal lineage is preferred and validated when present;
- missing reciprocal evidence is an actionable blocker for supersession, not a
  relation inferred from title/text similarity;
- lineage writes for target proposals remain separate supported operations.

## Read Compatibility

`ProposalLifecycleAuthorityService` selects by workspace schema:

```text
schema v3 -> require and validate ledger -> compare projections
schema v2 -> capture legacy projections once -> explicit legacy view
schema ahead -> unsupported
schema invalid/recovery required -> unresolved/blocked
```

The schema-v2 view has no event head and labels its source model
`legacy_projection_v2`. It can support reads and v2-safe unrelated writes, but
decision mutations fail operation compatibility before candidate generation.

## Preview And Apply

### Request Shape

`ProposalDecisionRequest` contains:

- proposal ID;
- event type;
- normalized reason/conditions;
- canonical decision date;
- operation key;
- actor/executor;
- optional owner approval context;
- optional accepted-decision readiness override request;
- optional affected/revocation event IDs;
- optional typed lineage;
- presentation limit/cursor excluded from semantics.

### Preview Flow

```text
check schema and recovery lock
-> capture proposal, ledger, projections and permissions once
-> resolve execution actor and owner authority
-> validate ledger and projection state
-> validate proposal-to-event semantic binding
-> capture readiness and render an override candidate when explicitly requested
-> normalize request and transition
-> capture/validate lineage targets
-> capture full impact when required
-> render candidate event, ledger and projections
-> validate candidate lifecycle view
-> build MutationPreview from every source and candidate
-> return semantic diff, bounded impact, blockers and apply ingredients
```

Preview does not create a cache, transaction directory, consent receipt,
registry or output file.

For an active-to-inactive event with a diverged proposal binding, preview is
applicable only with an explicit drift acknowledgement included in token
context. The semantic diff shows both stored accepted fingerprint and current
proposal fingerprint. Reinstatement and any event that activates current
proposal claims remain blocked.

### Token Context

The existing `MutationPreviewService` token context contains:

```yaml
proposal_id: PROP-102
operation_key: P2POP-...
event_type: revoked
source_head_event_id: PDE-...
proposal_semantic_sha256: ...
permission_policy_sha256: ...
owner_id: mrjungle
executor_actor_id: agent-id
lineage_sha256: ...
impact_source_fingerprint_sha256: ...
request_fingerprint_sha256: ...
decision_date: "2026-07-17"
```

### Apply Flow

```text
look for exact committed operation/preview binding
-> return already_applied or replay mismatch if found
-> rerun preview from submitted semantic request
-> compare preview token
-> require confirm
-> validate MCP consent binding when applicable
-> AtomicMutationWriter rechecks every source under lock
-> candidate validator parses ledger and projections through CandidateWorkspaceView
-> atomically replace ledger, proposal.md and decision.md, plus readiness.yml
   only when the accepted request carries an override
-> return event/lifecycle result
-> consume MCP consent with audit result
```

The exact-retry lookup occurs before evaluating a new default date. Public
apply requires the date and operation key returned by preview, so retries across
days remain exact.

### Projection Rendering

`proposal.md` changes only the `Status` section. The rest of the proposal bytes
are preserved by the section replacement helper and are source-preconditioned.

`decision.md` is fully engine-owned and rendered deterministically:

```markdown
# Decision - PROP-102

## Status

`revoked`

## Event Type

revoked

## Effective State

revoked

## Reason

...

## Date

2026-07-17

## Owner

mrjungle

## Ledger Head

PDE-...

## Decision Fingerprint

...

## Lineage

None.

## Canonical Source

decision-events.yml
```

For `reinstated`, Status/Effective State is the restored accepted outcome and
Event Type remains `reinstated`.

### Readiness Override

`proposal accept --override-readiness` remains one semantic decision request:

- preview captures the current readiness bytes and renders the exact override
  candidate without writing it;
- token context binds readiness source/candidate hashes, owner, reason and
  accepted event;
- apply adds `readiness.yml` to the atomic mutation targets;
- stale readiness, failed confirmation, transaction rollback or preview-only
  use leaves the old readiness bytes unchanged;
- no readiness override is created for non-acceptance events.

## Retry, Concurrency And Recovery

### Exact Retry

The ledger indexes operation keys and preview tokens during parse:

- same operation key + same request fingerprint + same preview token:
  `already_applied`;
- same operation key + different request fingerprint:
  `P2P366_DECISION_REPLAY_MISMATCH`;
- same preview token attached to another operation:
  integrity error;
- same event semantics under a new operation after state is already terminal:
  transition error, not another event.

### Concurrent Head

Both preview source preconditions and the candidate validator include head ID
and ledger bytes. The migration/mutation lock serializes writers. The losing
writer:

- returns `already_applied` if semantically identical;
- returns `P2P367_DECISION_CONCURRENT_HEAD` if different.

### Interrupted Mutation

Use existing `AtomicMutationWriter` states:

- before journal/replacement: rollback and clean;
- during replacement: reverse restoration from originals;
- failed restoration: preserve transaction and report recovery required;
- all unrelated governed writes remain blocked by migration lock;
- normal workspace recovery status/rollback/resume commands remain the
  recovery surface.

No decision-specific hidden recovery directory is introduced.

## Impact Model

### Captured Inputs

Capture once:

- proposal lifecycle views and ledgers;
- Change Set registry plus included/referenced proposal and decision bindings;
- Work manifests and scanned work summaries;
- software-spec status/source manifests;
- proposal vertical coverage and project evidence map;
- project projection manifest;
- decision-context index/topology diagnostics;
- conflict records and relation assertions;
- freshness graph;
- visible export/publication status.

Each collaborator returns typed data or one captured file set. The impact
service records source access counters for scale tests.

### Impact Item

```text
impact_id
dependency_kind
dependency_id
dependency_status
relationship
authority_effect
source_paths
source_fingerprint_sha256
remediation_kind
remediation_command
severity
```

Stable `impact_id` hashes proposal ID, source head, dependency kind, dependency
ID and relationship.

### Completeness And Pagination

The service builds and fingerprints the complete sorted tuple. `limit` and
cursor apply only to returned items. Preview includes:

- total count;
- returned count;
- omitted count;
- per-kind/per-status counts;
- completeness status;
- diagnostics;
- next cursor.

Any source parser error that could hide a dependency makes impact incomplete
and blocks apply. A known optional missing derived artifact may be advisory if
canonical dependency sources remain complete.

### Remediation Actions

`NextActionService` receives generated candidates after the lifecycle changes.
Examples:

```text
review_revoked_change / CHANGE-070
review_revoked_work / WORK-004
review_revoked_software_spec / CHANGE-070
review_revoked_vertical_evidence / PROP-102
refresh_decision_dependent_projection / project_projections
review_revoked_publication_source / publication_packet
```

ID:

```text
NEXT-DECISION-<event-id-prefix>-<dependency-kind>-<dependency-id>
```

The full stable identity is retained internally to detect prefix collisions.
Actions are ordered by criticality, dependency-kind rank, lifecycle-status rank
and ID.

## Legacy Migration

### Transition Metadata

```text
migration_id: workspace-v2-to-v3
source_version: 2
target_version: 3
inspect_requires: >=0.4.0,<0.5.0
plan_requires: >=0.4.0,<0.5.0
apply_requires: >=0.4.0,<0.5.0
dependencies:
  - workspace-legacy-to-v1
  - workspace-v1-to-v2
```

The final runtime ranges are updated consistently at release. Older
transitions remain supported by the 0.4 runtime if their fixture suites pass.

### Classification Matrix

| Proposal source | Decision source | Candidate |
| --- | --- | --- |
| draft/pending | missing or pending | empty resolved ledger |
| recognized equal decided state | usable fields | one migrated event |
| recognized equal state | missing optional fields | one event with explicit `unknown_legacy` field values and migration provenance, authority resolution according to required-field policy |
| recognized divergent states | any | unknown-legacy ledger, no event |
| unknown/malformed state | any | unknown-legacy ledger, no event |
| duplicate proposal ID or unreadable required file | any | migration blocker |

Owner and date are required to establish a resolved migrated event. If absent,
the source values are preserved but authority remains unknown. A valid outcome
alone is insufficient to invent owner authority.

### Candidate Rendering

For every proposal:

1. capture proposal/decision bytes and semantic sections;
2. classify legacy values;
3. render ledger;
4. render proposal status projection from ledger effective state;
5. render deterministic decision projection;
6. parse and cross-validate all three candidates;
7. add source preimages and candidate hashes to the plan.

The schema candidate is last and records migration ID, actor, apply timestamp
placeholder and plan fingerprint through the existing migration machinery.

### Legacy Authority Resolution

For an unknown-legacy ledger:

```text
p2p decision legacy-resolution preview PROP-XXX ...
p2p decision legacy-resolution apply PROP-XXX ... --preview-token ... --confirm
```

The owner selects a supported current outcome and supplies current rationale and
date. The first event includes migration-resolution provenance and references
the preserved legacy evidence digests. Historical timing remains
`unknown_legacy`; the current active interval begins at the curation event.

### Projection Repair

Projection repair is applicable only when:

- ledger is valid;
- lifecycle view is resolvable;
- only proposal status and/or decision projection diverge.

It uses the same actor, token and atomic writer contract.

### Ledger Repair

Ledger repair accepts an explicit candidate file:

- parse old bytes as far as safely possible;
- identify the maximal validated event prefix;
- parse candidate completely;
- require candidate to contain that exact prefix;
- require no changed event ID/hash/semantics in the prefix;
- allow restoration of missing/corrupt suffix only when predecessor hashes
  prove continuity;
- bind source file digest and candidate digest to preview;
- require owner apply and atomic projection regeneration.

If continuity cannot be proven, the service reports a blocker. It never guesses
or truncates.

## Consumer Convergence

| Consumer | Current issue | Target integration |
| --- | --- | --- |
| Proposal document/view | parses two Markdown files and permits decided-body edits | inject lifecycle view; render additive head/history/binding fields; gate semantic updates |
| Proposal review artifacts | treats decision.md canonical | classify ledger canonical, decision.md projection |
| Validation | compares selected tokens | validate ledger, chain and projections |
| Registries | reads current decision.md | lifecycle current record plus head/fingerprint metadata |
| Change creation | exact status `accepted` | require active authority; bind event head/fingerprint |
| Change status/preflight | no later revocation model | preserve object and emit source-authority diagnostic |
| Work planning | trusts Change source list | block new work on inactive/unresolved governing source |
| Software spec | accepted source only | bind lifecycle event/fingerprint and expose inactive source |
| Project projection | filters parsed status | consume captured lifecycle map |
| Progress/maturity/assessment | duplicated active policy | active/historical axes from lifecycle map |
| Vertical evidence | proposal status lookup | activate mapping only for active authority |
| Decision context | decision.md canonical | ledger source and event extraction |
| Relations/conflicts | file assertions only | validate event lineage and authority |
| Next actions | no revocation remediation | generated deterministic dependency review actions |
| Freshness | proposal glob without event policy | ledger/policy versions and head fingerprints |
| Visible export/publication | current decision text | explicit active/historical/unresolved rendering |
| Context packet/intake | status-derived authority | head-bound lifecycle and retrieval records |

### Captured Lifecycle Map

Broad services receive a request-scoped mapping:

```text
proposal_id -> ProposalDecisionLifecycleView
```

One discovery pass builds the map. A service processing 100 proposals must not
call `find_proposal_dir()` and reparse the ledger for each nested relation.

### Change Set Decision Binding

New `included-decisions.yml` entries add:

```yaml
- proposal: PROP-102
  decision_file: .p2p/proposals/.../decision.md
  decision_ledger: .p2p/proposals/.../decision-events.yml
  head_event_id: PDE-...
  decision_semantic_sha256: ...
```

Existing entries remain readable. Their current source binding is resolved at
read time; no mass Change Set rewrite occurs during v2-to-v3 migration.

### Source-Authority Behavior

- New Change Set: active source and `proposal_binding_status=current` required.
- Existing planned/in-progress Change with inactive source: implementation
  preflight blocker and remediation action.
- Existing active decision with diverged proposal claims: source-binding blocker
  without an implicit revocation.
- Existing completed Change with inactive source: historical impact advisory,
  no status mutation.
- New Work/spec refresh on unresolved source: blocker.
- Existing generated spec: stale/inactive-source status, no overwrite.
- Project/vertical active views: source excluded from active numerator but kept
  in historical evidence.

## Decision Context Design

### Source Catalog

Schema v3 descriptors:

- `proposal.md`: proposal body, canonical semantic content excluding status
  authority.
- `decision-events.yml`: canonical proposal decision ledger.
- `decision.md`: derived projection, available for traceability but not
  separately extracted as decision authority.

Schema v2 descriptors remain proposal body + legacy decision projection.

### Event Records And Nodes

Add stable event nodes:

```text
decision-event:<proposal-id>:<event-id>
```

Relations:

- event `decides` proposal;
- event `follows` predecessor;
- revoke/reinstate `affects_decision` prior event;
- supersede/split/merge event emits typed proposal lineage;
- active interval links event boundaries.

Evidence points to YAML field fragments or structured paths with ledger source
digest. `decision.md` cannot create duplicate event records.

### Authority

Policy v2 maps:

- current accepted/conditional head or reinstated interval: active accepted
  authority;
- prior accepted events: historical previously-active authority;
- deferred: unresolved historical context;
- rejected/withdrawn: historical never-active;
- revoked/replaced heads: historical previously-active;
- unknown legacy: unknown/unresolved;
- projection divergence: diagnostic only; ledger remains controlling if valid.

### Retrieval

Existing score policy gains an authority rank, not an arbitrary textual boost.
For otherwise equal records:

```text
active accepted
active conditional
explicit project/choice authority
historical previously-active
historical never-active
unresolved legacy
```

Packets expose the rank reason, head binding and historical label.

## CLI Contract

### Read Commands

```text
p2p decision status PROP-XXX [--format text|json]
p2p decision history PROP-XXX [--limit N] [--cursor CURSOR] [--format text|json]
p2p decision impact PROP-XXX --event EVENT [request fields] [--limit N] [--cursor CURSOR]
```

History default limit is 20 and maximum 100. Cursor binds proposal ID, ledger
head, policy version and last stable sort key.

### Mutation Commands

```text
p2p decision preview PROP-XXX --event EVENT --reason TEXT --actor OWNER \
  [--decided-on YYYY-MM-DD] [--operation-key KEY] [lineage/reference options]

p2p decision apply PROP-XXX --event EVENT --reason TEXT --actor OWNER \
  --decided-on YYYY-MM-DD --operation-key KEY --preview-token TOKEN --confirm \
  [lineage/reference options]
```

Preview output returns the normalized date and operation key that apply must
reuse. Text output includes a shell-safe conceptual next command but does not
promise exact shell quoting for arbitrary reason text; JSON is the automation
surface.

Repair commands:

```text
p2p decision repair projection preview|apply PROP-XXX ...
p2p decision repair ledger preview|apply PROP-XXX --source PATH ...
p2p decision legacy-resolution preview|apply PROP-XXX ...
```

### Compatibility Commands

`proposal accept`, `proposal reject`, `proposal defer` and `decision record`:

- accept the existing semantic options;
- accept additive operation/date/token/confirm options;
- retain `proposal accept --override-readiness` as an optional source-bound
  candidate committed only with accepted apply;
- without token, render the shared preview and report `preview_required`;
- with matching token and confirm, call shared apply;
- never call a direct projection writer.

Automation must migrate to JSON preview/apply. Help and release notes call out
the intentional two-step safety change.

## MCP Contract

### Tools

Add or stabilize:

```text
p2p_proposal_decision_status
p2p_proposal_decision_history
p2p_proposal_decision_preview
p2p_proposal_decision_apply
p2p_proposal_decision_projection_repair_preview
p2p_proposal_decision_projection_repair_apply
p2p_proposal_decision_ledger_repair_preview
p2p_proposal_decision_ledger_repair_apply
p2p_proposal_decision_legacy_resolution_preview
p2p_proposal_decision_legacy_resolution_apply
```

The exact number of tools may be reduced with an explicit typed `repair_mode`,
but read/write permission classes and schemas must remain unambiguous.

### Consent Binding

Decision apply consent:

```text
operation: proposal_decision_apply
target: PROP-102@<preview-token>
actor_id: executor
approved_by: current-owner
```

The handler validates:

- receipt granted and unused;
- operation/target/actor exact match;
- approver still resolves as owner;
- preview token and owner permission digest still current.

On success it consumes consent with event ID/head. On a failure after a
possible head change it uses the existing `used_with_error` audit path.

For response-loss retry, a consumed receipt is accepted only as idempotency
evidence when its recorded result exactly matches proposal ID, operation key,
preview token and committed event ID. It authorizes no new write. A consumed
receipt with missing or different result binding remains invalid.

Legacy MCP accept/reject/defer tools delegate to preview/apply compatibility
logic and cannot consume old unbound consent for a v3 decision.

## Pre-Migration Owner Attestation

### D022 - Extend The Existing Migration Input Contract

The v2-to-v3 planner consumes owner attestations through the existing
`--input` patch, plan fingerprint and lock-protected apply protocol. No second
decision write surface or persistent preview cache is introduced.

```yaml
proposal_decisions:
  attestation_contract_version: 1
  authority_attestations:
    PROP-001:
      owner_id: mrjungle
      legacy_status: accepted
      legacy_approver: local
      decided_on: 2026-05-19
      source_sha256:
        proposal.md: <64 lowercase hex>
        decision.md: <64 lowercase hex>
```

`accepted_with_changes` additionally requires a non-empty `conditions` list
with stable `id` and `text` fields. Every mapping is closed and normalized by
proposal and condition ID before fingerprinting.

### D023 - Separate Legacy Provenance From Current Authority

An attestation means the current declared owner has reviewed the exact legacy
sources and authorizes their values as the initial v3 decision. The event
authority is therefore the current owner and uses channel
`workspace_migration_owner_attestation`. Migration provenance separately
preserves the original approver, status, date, reason, source hashes and
attestation contract. The implementation never adds old actors to permissions
or claims they were current owners.

### D024 - Source-Bound Eligibility And Fail-Closed Semantics

Attestation eligibility requires:

1. aligned proposal status, decision status and outcome;
2. non-empty rationale, legacy approver and valid ISO decision date;
3. exact `proposal.md` and `decision.md` SHA-256 matches;
4. an attesting identity with current `owner` role;
5. an initial event type that does not require predecessor or lineage history.

The accepted initial set is `accepted`, `accepted_with_changes`, `deferred`,
`withdrawn` and `rejected`. `superseded`, `revoked`, split and merge outcomes
remain loss-aware `unknown_legacy`; converting them to one initial event would
fabricate history.

Malformed attestation structure is rejected while loading the input patch.
Source, owner or summary mismatch produces
`P2P390_MIGRATION_ATTESTATION_INVALID`, marks the plan non-applicable and leaves
the source-preserving unknown ledger candidate visible for diagnosis.

### D025 - Deterministic Read-Only Template

`p2p workspace migrate attestation-template --to 3 --owner OWNER` captures the
same workspace snapshot used by migration planning and emits:

- the unmodified source-plan fingerprint;
- a normalized owner-input patch for eligible simple outcomes;
- included proposal IDs;
- manual-review entries for accepted-with-changes conditions, lineage-dependent
  histories and other unsafe sources.

The command performs no write and never inserts placeholder conditions.
Operators copy or transform the emitted `owner_input` into a reviewed YAML
patch. The regular `plan --input` command remains the only way to obtain the
applicable attested plan fingerprint.

### D026 - Release And Migration Ordering

This hardening changes source after runtime `0.4.0`. It therefore requires a
new tested patch runtime, explicit owner-authorized release, isolated install
and source/installed parity check before repository migration resumes. M-T008
must use that installed runtime; source-checkout execution is not acceptable
evidence for the repository apply gate.

## Diagnostics

Reserve `P2P360` through `P2P389` for this lifecycle. Initial assignments:

| Code | Meaning |
| --- | --- |
| P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED | legacy evidence cannot establish authority |
| P2P361_DECISION_LEDGER_INVALID | ledger schema or chain invalid |
| P2P362_DECISION_PROJECTION_DIVERGENCE | projection differs from valid ledger |
| P2P363_DECISION_TRANSITION_INVALID | requested event not allowed |
| P2P364_DECISION_OWNER_REQUIRED | owner authority missing |
| P2P365_DECISION_STALE_PREVIEW | source changed after preview |
| P2P366_DECISION_REPLAY_MISMATCH | operation key reused with different semantics |
| P2P367_DECISION_CONCURRENT_HEAD | apply lost head race |
| P2P368_DECISION_REINSTATEMENT_MISMATCH | exact decision cannot be restored |
| P2P369_DECISION_LINEAGE_INVALID | lineage target or relation invalid |
| P2P370_DECISION_IMPACT_INCOMPLETE | dependency scan cannot prove completeness |
| P2P371_DECISION_PREVIEW_REQUIRED | compatibility command needs two-phase apply |
| P2P372_DECISION_REPAIR_UNSAFE | repair would rewrite valid history |
| P2P373_DECISION_SOURCE_CHANGED | source changed during request capture |
| P2P374_DECISION_CONSENT_MISMATCH | consent is not token/owner bound |
| P2P375_DECISION_SCHEMA_V3_REQUIRED | event write attempted on older schema |
| P2P376_DECISION_FUTURE_CONTRACT | future ledger/event policy unsupported |
| P2P377_DECISION_PROPOSAL_BINDING_DIVERGED | current proposal claims differ from controlling event |

Unused codes remain reserved. Workspace operation compatibility may still emit
its existing generic schema diagnostic with P2P375 as domain detail.

## Validation

Global validation order:

1. workspace schema and recovery;
2. proposal identity/directory;
3. schema-specific decision source contract;
4. ledger parse and chain integrity;
5. lifecycle derivation;
6. projection equality;
7. lineage target validation;
8. registry/freshness checks.

A valid v3 ledger plus divergent projection is a repairable warning/error based
on affected field. Invalid ledger is an authority-blocking error. Unknown
legacy authority is a visible blocking diagnostic for decision revisions but
does not make unrelated project reads impossible.

## Freshness And Derived Ownership

Update policy versions and source sets:

- canonical source fingerprint includes `decision-events.yml`;
- project projection source fingerprint includes active head/fingerprint;
- decision context semantic fingerprint includes event chain and authority
  policy;
- software spec input includes bound decision head/fingerprint;
- next actions depend on decision authority and impact;
- visible export/publication becomes stale when its active/historical decision
  classification changes.

Projection-only repair changes do not semantically stale consumers whose
recorded ledger head is unchanged. Physical manifests that own projection bytes
may still require a deterministic refresh according to their explicit source
contract.

## Test Strategy

### Pure Unit Tests

- strict ledger parser/serializer and duplicate keys;
- proposal/decision fingerprints;
- event IDs, hashes and collision checks;
- complete transition matrix;
- lineage validation;
- authority interval derivation;
- legacy classification matrix;
- cursor and impact ordering.

### Service Tests

- fresh ledger creation and status/history;
- preview/apply for every event;
- exact retry and replay mismatch;
- proposal update and current-event semantic binding;
- owner and delegated MCP authority context;
- proposal/projection/permissions/lineage/impact staleness;
- legacy resolution and repairs;
- generated remediation actions;
- all consumer adapters.

### Transaction Tests

Inject failure:

- after source recheck;
- before/after staging;
- before/after candidate validation;
- before/after journal;
- before/after each of the three replacements;
- during rollback;
- during cleanup.

Assert byte invariance, full commit or recovery-required journal.

### Migration Tests

Fixtures:

- empty v2 project;
- draft/pending proposals;
- every recognized current outcome;
- missing optional and required legacy fields;
- malformed YAML/Markdown;
- projection divergence;
- duplicate proposal IDs;
- unknown files;
- 100 proposals;
- composed v0-to-v3.

Test plan determinism, ownership, no writes, apply, rollback, resume, no-op,
external changes and ahead/older runtime behavior.

### Public Contract Tests

- CLI text/JSON status, history, preview, apply, impact and repair;
- compatibility command safety;
- MCP catalog schemas, read parity, token-bound consent and audit;
- validation/doctor/context/next diagnostics;
- additive registry/project/export serialization.

### Consumer Regression Tests

For each consumer, create a valid ledger and deliberately corrupt only the
projection. The consumer must either use ledger authority or report projection
drift; it must never adopt the corrupt status.

Then revoke the decision and assert:

- active project/vertical views exclude it;
- history and rationale remain;
- dependencies remain physically unchanged;
- preflight and next actions report remediation;
- freshness and source fingerprints change semantically.

Also change accepted proposal body bytes directly and assert the event remains
historically active while every claim-consuming projection/preflight reports
binding divergence instead of accepting the changed text or treating it as a
revocation.

### Scale And Metamorphic Tests

- 100 proposals, at least 20 with 3-5 events;
- varied Change/Work/spec dependencies;
- shuffled filesystem enumeration;
- different absolute roots and clocks;
- stable event/context/impact ordering and hashes;
- bounded read counters;
- bounded text/JSON payloads with complete internal impact fingerprints.

## Release And Repository Dogfooding

### Gate 1 - Engine Completion

- all feature slices implemented;
- requirement/design/task/test matrix current;
- focused, public and full suites pass;
- version and docs consistent;
- wheel/sdist and isolated install pass;
- v2 read and v2-to-v3 migration fixtures pass.

### Gate 2 - Runtime Publication

Only after owner confirmation:

- create the intended release commit/tag;
- build and verify artifacts from that exact commit;
- publish the runtime artifact;
- verify installation outside the source tree.

Source checkout availability is not a substitute for a reproducible installed
runtime when the repository runtime contract points collaborators to a released
version.

### Gate 3 - Repository Runtime Alignment

Through supported P2P runtime preview/apply:

- update `recommended` to the verified `0.4.x` release;
- update `requires` to the approved compatible range;
- validate the active executable against the contract.

Do not edit `.p2p/project/runtime.yml` manually.

### Gate 4 - Repository V2-To-V3 Plan

Capture:

- `p2p runtime status --format json`;
- `p2p workspace schema status --format json`;
- `p2p validate`;
- registries, proposal/decision counts and lifecycle distribution;
- freshness and publication status;
- `p2p workspace migrate plan --to 3 --format json`.

Review every unknown-legacy or blocking proposal before apply.

### Gate 5 - Apply And Authority Curation

- apply the reviewed plan with owner confirmation;
- recover immediately if required;
- run validation;
- resolve only genuinely ambiguous legacy authority through the explicit
  primitive, one proposal at a time;
- never edit ledgers or projections manually.

### Gate 6 - Derived Alignment

Inspect and refresh in dependency order:

```text
registries
project projections
decision context
assessment and maturity/progress
software specs
next actions
visible export
publication packet/curation/validation/render
owner publication review
```

Only deterministic stages are auto-refresh candidates. Agent-curated and
owner-review stages remain explicit.

### Gate 7 - Final Comparison

Compare pre/post:

- total proposals and current state distribution;
- accepted authority count and previously-active count;
- event and unresolved-legacy counts;
- Change/Work/spec dependency diagnostics;
- vertical evidence and progress axes;
- registry/context/projection fingerprints;
- derived freshness;
- publication approval state.

Record residual manual actions with supported commands and owner authority.

## Risks And Mitigations

- Risk: direct status readers remain hidden.
  Mitigation: source inventory, injected lifecycle maps, projection-corruption
  consumer tests and final `rg` audit.

- Risk: migration fabricates historical authority.
  Mitigation: required field policy, unknown-legacy ledger, no Git/mtime
  inference and explicit owner resolution.

- Risk: event YAML grows over many revisions.
  Mitigation: bounded history API and compact structured events; no duplicated
  event history in registries. The future compaction feature may summarize only
  with head/interval bindings.

- Risk: preview impact is expensive.
  Mitigation: captured registries/indexes, one-pass dependency maps, source
  counters and scale gates.

- Risk: event apply and consent audit diverge.
  Mitigation: token-bound consent, shared service and used-with-error handling.

- Risk: projection repair becomes a history rewrite backdoor.
  Mitigation: separate repair modes, maximal valid prefix rule and owner
  preview/apply.

- Risk: a revoked source blocks legitimate remediation specs.
  Mitigation: distinguish normal implementation preflight from explicit
  remediation workflows; preserve dependent objects and provide targeted next
  actions.

- Risk: v3 runtime deployment repeats earlier local/source installation
  confusion.
  Mitigation: separate engine completion, reproducible release, installed
  runtime verification, runtime contract update and repository migration gates.

## Deferred Follow-Ups

- Thematic consolidation and compaction of related accepted decision memory.
- Cross-project or server-side decision event storage.
- Provider-backed signed owner attestations.
- Cryptographic signatures beyond local hash-chain integrity.
- Automated technical rollback orchestration after revocation.
