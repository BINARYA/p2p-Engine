# Proposal Decision Revision and Revocation Lifecycle

## Provenance

- Proposal: PROP-102
- Source: .p2p/proposals/PROP-102-proposal-decision-revision-and-revocation-lifecycle

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

## Decision

# Decision - PROP-102

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

La proposta definisce in modo completo e verificabile il lifecycle delle decisioni, distinguendo rifiuto, revoca, sostituzione e reinstatement, con autorita owner, migrazione legacy, impatto sui consumer e criteri di robustezza. La readiness e decision_ready al 100%, con confidenza alta e senza gap o gate falliti.

## Date

2026-07-17

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-568a29c09673a60b82d5ae8a

## Decision Fingerprint

9515a8ba8394a52c529447f48a92829513ccce7127ce2a5378dc8f551374fc13

## Lineage

None.

## Canonical Source

decision-events.yml
