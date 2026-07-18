---
change_id: CHANGE-070
title: Proposal Decision Revision and Revocation Lifecycle
status: in_progress
created_at: '2026-07-17'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-102
  accepted_decisions: []
implementation_targets:
- local_cli
spec_targets:
- p2p_spec
export_targets:
- openspec
- speckit
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-070 - Proposal Decision Revision and Revocation Lifecycle

## Summary

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

## Rationale

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

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Change Set metadata.

## Acceptance Criteria

- Change Set metadata is present and reviewable.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
