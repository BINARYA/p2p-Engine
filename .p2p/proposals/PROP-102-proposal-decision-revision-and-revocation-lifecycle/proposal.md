# PROP-102 - Proposal Decision Revision and Revocation Lifecycle

## Status

`accepted`

## Problem

P2P currently represents a proposal decision primarily as one current outcome.
The decision write path replaces `decision.md` and then replaces the status in
`proposal.md`, without validating the previous lifecycle state or preserving a
queryable sequence of owner decisions.

As a result, an accepted proposal can be rewritten as rejected. The current
workspace then appears to say that the proposal was never adopted, even though
it may already have influenced project definition, Change Sets, Work,
specifications, implementation, publication and later decisions. Git can
recover earlier bytes, but normal validation, retrieval and derived-state
consumers do not use Git history as the proposal decision model.

The model also lacks a precise distinction between rejection before adoption,
withdrawal before decision, revocation after acceptance, replacement,
reinstatement and downstream deprecation. Without that distinction, future
decision-memory consolidation cannot reliably determine which decisions are
active, historical, previously active, replaced or merely deferred.

## Context

P2P already supports `accepted`, `accepted_with_changes`, `rejected`,
`deferred`, `split`, `merged_into_other` and `superseded` outcomes. Decision
context assigns active or historical authority to these outcomes, while project
projections generally include accepted decisions and exclude inactive ones.
These consumers currently infer authority from one stored status and one
decision artifact.

The missing capability is not the initial reject command. It is a revision
lifecycle that preserves historical truth when the owner changes a decision
after it has become effective.

The following terminology is owner-confirmed:

- `withdrawn`: an undecided proposal abandoned before adoption;
- `rejected`: a proposal evaluated but never adopted;
- `revoked`: a previously accepted decision cancelled without replacement;
- `superseded`: a previously effective decision replaced through explicit
  lineage;
- `deprecated`: a downstream operational state, not a terminal proposal
  decision outcome;
- `reinstated`: an event that restores the exact same previously revoked
  decision under strict identity and impact checks.

Changing normative authority does not change physical reality. Revoking a
decision does not prove that code was rolled back, a deployment was reverted or
dependent delivery work was cancelled.

## Goals

- Preserve an append-only, queryable history of proposal decision events,
  including rationale, owner authority, date, predecessor and lineage.
- Derive current proposal status and authority deterministically from the valid
  event sequence.
- Define an exhaustive transition matrix with exact retry, invalid transition
  and reconsideration behavior.
- Distinguish initial rejection from withdrawal, revocation, supersession,
  reinstatement and downstream deprecation.
- Make decision mutations owner-controlled, previewed, source-bound,
  stale-safe, atomic, idempotent where appropriate and recoverable.
- Keep current CLI and human-readable status views available as projections
  during a forward compatibility transition.
- Migrate current single-decision artifacts without inventing missing owner
  evidence or erasing legacy values.
- Propagate lifecycle authority consistently to validation, registries,
  project projections, decision context, relations, vertical evidence, Change
  Sets, Work, software specifications, next actions and publication.
- Produce explicit impact and remediation guidance without automatically
  changing dependent owner-controlled lifecycles.
- Establish the stable authority and lineage contract required by future
  thematic decision-memory consolidation.

## Non-Goals

- Physically delete accepted, rejected, revoked or superseded proposals.
- Rewrite history so that a previously accepted decision appears never to have
  been active.
- Automatically roll back source code, deployments, completed Change Sets,
  Work or external effects.
- Automatically cancel, supersede, complete or reopen dependent lifecycle
  objects.
- Implement thematic proposal compaction, persistent decision-context caching
  or publication curator refinement.
- Treat `deprecated` as another proposal decision outcome.
- Allow an agent-supplied actor string to establish owner authority.
- Conflate proposal-decision rejection with managed proposal-branch rejection.

## Proposal

### Decision Event Model

Introduce one versioned canonical decision-event ledger per proposal. The
ledger is the semantic source for proposal decision history. `proposal.md`
status and the human-readable current decision remain compatible projections
of the ledger rather than independent authority sources.

Every event must include enough structured data to validate and reconstruct the
lifecycle:

- schema and event identity;
- proposal identity;
- event type and resulting effective state;
- rationale;
- owner/approver identity and validated authority provenance;
- canonical decision date;
- predecessor event identity and integrity evidence;
- semantic fingerprint of the decision being affected;
- optional replacement, split or merge lineage;
- optional impact-preview binding;
- migration provenance when derived from a legacy artifact.

Audit timestamps, file mtimes and Git author metadata must not determine event
identity or manufacture owner evidence. The design will define the exact file
name, serialization, predecessor/hash protection and recovery format. Replacing
the single-ledger direction requires explicit technical evidence.

### Effective State Projection

Current status, decision authority and active/historical classification are
derived from the validated event head and lineage. A stored projection that
does not match the ledger is stale or invalid; it cannot silently override the
ledger.

The public vocabulary has distinct meanings:

| Event or state | Preconditions | Effective result |
| --- | --- | --- |
| `accepted` | Proposal has never been active, or exact retry | Active |
| `accepted_with_changes` | Proposal has never been active, or exact retry | Active and qualified |
| `deferred` | Proposal is undecided, or exact retry | Unresolved |
| `withdrawn` | Proposal has never been active | Historical, never active |
| `rejected` | Proposal has never been active | Historical, never active |
| `revoked` | Current authority is accepted or conditionally accepted | Historical, previously active |
| `superseded` | Current authority is active and replacement lineage is valid | Historical with explicit replacement |
| `split` | Valid explicit split targets exist | Historical with split lineage |
| `merged_into_other` | Valid explicit merge target exists | Historical with merge lineage |
| `reinstated` | Exact previously revoked decision is restored | Returns to the referenced prior active authority |

`deprecated` belongs to downstream operational policy and cannot be used to
replace a proposal decision event.

Rejected or withdrawn proposals are reconsidered through a new linked proposal.
A revoked decision may be reinstated only when:

- its semantic fingerprint is identical to the referenced prior decision;
- the revocation event is referenced explicitly;
- a current impact preview is bound to the operation;
- owner authority is validated again;
- no dependent technical effect is assumed to be restored.

Any changed content, condition or constraint requires a new linked proposal.

### Transition And Retry Rules

The implementation specification must provide a complete matrix for every
current state and requested event. Invalid transitions fail before writes.

Repeating the exact same operation with the same source head, semantic payload,
owner authority and idempotency identity returns the already-applied result.
Reusing an operation identity with different inputs, applying against a changed
head or attempting to reorder history fails with a stable diagnostic.

The model must also specify:

- whether an event is terminal or may have a later valid successor;
- required lineage fields;
- no-op and exact-retry behavior;
- stale preview behavior;
- concurrent-head conflict behavior;
- recovery after interruption;
- explicit repair behavior for corrupted or divergent projections.

### Governed Mutation

All decision writes use one domain service shared by CLI and permission-gated
MCP. A write requires:

1. validated owner authority;
2. current workspace compatibility;
3. valid current ledger and projection;
4. a source-bound preview token;
5. confirmation for authority-changing operations;
6. unchanged proposal, ledger head, permissions and relevant impact sources;
7. atomic replacement of the ledger and all engine-owned projections;
8. deterministic exact-retry behavior.

Managed branch accept/reject operations remain separate collaboration
operations and cannot create or revise proposal decision events implicitly.

### Revocation Impact And Remediation

Revocation remains available to the owner even when Change Sets, Work,
specifications, vertical evidence or implemented behavior depend on the
decision. Before revocation, the system produces a bounded impact preview that
identifies:

- active and completed dependent lifecycle objects;
- affected vertical sections and project projections;
- decision-context and relation consequences;
- stale generated artifacts;
- possible conflicts with other active decisions;
- remediation, replacement or rollback actions requiring separate governance.

After confirmation, revocation removes the decision from active authority,
preserves its previously active interval and emits stable remediation next
actions. It does not mutate dependent lifecycle states, remove implementation
evidence or claim that remediation is complete.

### Legacy Compatibility And Migration

The canonical ledger changes workspace decision semantics and therefore
requires a registered forward workspace-schema transition from the current
schema to the next supported schema. Older workspaces remain readable through
an explicit compatibility layer, while event-dependent writes are blocked
until a safe migration is applied.

For an aligned legacy proposal, the current decision is preserved as the first
ledger event with legacy provenance. Migration must:

- retain every valid value;
- preserve readable original malformed values as evidence;
- use `unknown_legacy` for missing or unusable fields;
- never infer owner, date or rationale from Git metadata or mtimes;
- diagnose proposal/decision status divergence;
- mark authority unresolved when the outcome cannot be established;
- block later decision revisions until owner curation resolves authority
  ambiguity;
- remain dry-run plannable, atomic, idempotent, recoverable and forward-only;
- avoid fabricating prior events that are not present in canonical evidence.

### Consumer Convergence

One lifecycle-authority service must drive every consumer. At minimum, the
implementation must reconcile:

- proposal show/list/status and registries;
- validation and migration diagnostics;
- project status, progress, maturity and assessment;
- active proposal projections and vertical evidence;
- decision-context extraction, authority, topology and retrieval;
- relations, conflicts, split/merge/supersession lineage;
- Change Set and Work preconditions and impact reporting;
- software-spec lifecycle and freshness;
- managed next actions;
- visible project export and publication;
- future thematic decision-memory consolidation.

Inactive decisions remain retrievable as historical rationale and alternatives,
but cannot be presented as current constraints. A future consolidated memory
record must bind to event head, authority interval, lineage and source
fingerprint so that revocation or reinstatement invalidates stale summaries.

## Alternatives

### Keep Overwriting And Rely On Git

This avoids a schema change but leaves normal project memory unable to represent
decision history, permits partial-write divergence and makes consolidation
unsafe. Rejected.

### Require A New Corrective Proposal Without A Revocation Event

This preserves the original acceptance and is useful for remediation, but does
not itself remove the old decision's authority. Every consumer would need to
infer cancellation from a relation that may be absent. Rejected as the
authority model, retained as a remediation pattern.

### Append-Only Events With Derived Effective State

This preserves history, supports explicit authority transitions and gives
retrieval and consolidation a stable contract. It introduces migration and
cross-consumer work but directly addresses the demonstrated failure. Selected.

### Individual Immutable Event Files Plus A Manifest

This can isolate individual event corruption but introduces manifest/event
consistency, multi-file ordering and larger migration complexity. A single
versioned ledger per proposal is selected because event volume is small and
atomic replacement is simpler.

## Impacts

The change affects proposal decision models and commands, persistence,
workspace schema migration, validation, permissions and consent, MCP
governance tools, lifecycle authority, registries, project projections,
decision context, vertical coverage, Change Sets, Work, software specs, next
actions and publication.

It extends the foundations established by proposal decision shortcuts,
governance policy, persistence boundaries, workspace migration and decision
context. It does not supersede those capabilities. The future decision-memory
consolidation feature depends on the authority contract introduced here.

The implementation should be delivered in bounded slices:

1. domain vocabulary, event contract and exhaustive transition matrix;
2. ledger persistence, projections, preview and atomic mutation;
3. legacy compatibility, forward migration and recovery;
4. CLI and permission-gated MCP parity;
5. downstream consumer convergence and remediation actions;
6. validation, performance, documentation and full migration evidence.

## Risks

- **Vocabulary complexity:** Too many states could confuse users. Mitigate with
  a small public vocabulary and separate decision, authority and operational
  states.
- **Partial consumer migration:** Some services could continue trusting legacy
  status. Mitigate with one authority facade, a consumer inventory and contract
  tests.
- **False rollback claims:** Revocation could be mistaken for technical
  remediation. Keep normative authority and implementation state separate.
- **Concurrent event heads:** Two decisions may target the same predecessor.
  Use source-bound previews, locking, head checks and idempotency identities.
- **History mutation:** Generic updates could reorder or rewrite events.
  Validate predecessor/integrity chains and prohibit silent normalization.
- **Broken replacement lineage:** A supersession target may be missing or
  inactive. Validate target identity and authority before activation.
- **Authority bypass:** CLI and MCP could diverge or trust caller-controlled
  actor text. Resolve authority centrally and bind consent to operation inputs.
- **Legacy ambiguity:** Old artifacts may lack reliable metadata. Preserve
  `unknown_legacy`, emit diagnostics and require owner curation before revision.
- **Stale consolidation:** A summary may omit a later revocation. Bind future
  summaries to the authoritative event head and lifecycle policy version.
- **Migration blast radius:** The new source contract affects many consumers.
  Require dry-run, recovery, focused consumer tests and a full repository
  migration rehearsal before release.

## Open Questions

All owner-policy questions raised during exploration have been answered and are
recorded in structured question state and `clarifications.md`.

The following are implementation-design obligations rather than unresolved
owner decisions:

- exact ledger filename and serialization;
- event identity, predecessor and integrity-hash formula;
- lock, atomic replacement and recovery mechanics;
- compatibility-window and next workspace schema details;
- complete downstream invalidation graph;
- exact current-decision projection format;
- bounded impact-preview and remediation-action payloads;
- performance ceilings for large histories and workspaces.

Vertical coverage remains subject to a separate owner-reviewed mapping.

## Acceptance Criteria

- The public model defines mutually exclusive semantics for withdrawal,
  rejection, revocation, supersession, reinstatement and downstream
  deprecation.
- A versioned canonical ledger preserves every valid decision event; supported
  operations cannot overwrite, delete or reorder prior history.
- Current proposal status and current-decision views are deterministic
  projections and validation detects divergence.
- The specification contains an exhaustive state/event transition matrix,
  including prerequisites, lineage, exact retry, no-op and prohibited cases.
- Initial rejection is allowed only before adoption; reversing an accepted
  decision records revocation or supersession and preserves the acceptance.
- Reinstatement is accepted only for an identical semantic fingerprint, a
  referenced revocation, current impact preview and new owner authorization.
- Changed content, conditions or constraints require a new linked proposal.
- Authority-changing operations require owner authority, source-bound preview,
  confirmation, unchanged preconditions, locking and atomic replacement.
- Exact retries are idempotent; divergent token reuse, concurrent heads and
  stale sources fail without partial writes.
- CLI and permission-gated MCP call the same lifecycle service and expose
  equivalent results and diagnostics.
- Proposal-decision rejection and managed-branch rejection remain separate and
  cannot trigger each other implicitly.
- Revocation impact preview identifies active and completed dependencies,
  affected authority, stale artifacts and explicit remediation options.
- Revocation does not automatically mutate Change Set, Work, specification,
  implementation, deployment or external lifecycle state.
- Revoked, rejected, withdrawn, split, merged and superseded decisions remain
  available as correctly labelled historical context.
- Inactive decisions are excluded from active project projections and cannot be
  rendered as current constraints.
- Existing single-decision workspaces remain readable and have a deterministic,
  registered, forward-only migration to the next workspace schema.
- Migration preserves valid legacy values, represents missing or malformed data
  as `unknown_legacy`, retains provenance and never infers owner evidence from
  Git metadata.
- Ambiguous legacy authority blocks later revision but does not prevent
  loss-aware preservation of the historical record.
- Migration is dry-run plannable, atomic, idempotent, recoverable and covered by
  aligned, divergent, malformed, interrupted and concurrent fixtures.
- Every downstream consumer uses the centralized lifecycle-authority contract
  or an explicitly versioned compatible projection.
- Stable next actions distinguish decision remediation from technical rollback
  and do not duplicate on repeated refresh.
- Future consolidated memory can bind to stable event identity, effective
  authority, lineage and freshness without reading an overwrite-shaped
  decision.
- Documentation explains the lifecycle, migration, owner boundary, branch
  distinction and non-automatic rollback behavior.
- Focused, public, full and migrated-workspace validation complete without
  unexplained errors, warnings or canonical history loss.

## Decision

Pending.
