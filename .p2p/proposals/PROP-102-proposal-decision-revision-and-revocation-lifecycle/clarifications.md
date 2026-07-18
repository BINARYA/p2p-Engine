# Clarifications - PROP-102

## Resolved Terminology

1. `withdrawn` identifies a proposal abandoned before adoption.
2. `rejected` identifies a proposal evaluated but never adopted.
3. `revoked` identifies a previously accepted decision cancelled without a
   replacement.
4. `superseded` identifies a previously effective decision replaced through
   explicit lineage.
5. `deprecated` is a downstream operational state, not a terminal proposal
   decision outcome.

These meanings are mutually exclusive and must be shared by validation,
authority projection, CLI, MCP, migration, retrieval and publication.

## Resolved Revocation Policy

The owner may revoke a decision even when Change Sets, Work, specifications or
implemented behavior depend on it. The operation requires a current impact
preview. It removes normative authority and generates explicit remediation,
replacement or rollback actions, but it does not mutate dependent lifecycles or
claim that technical effects have already been reversed.

## Resolved Reinstatement Policy

An owner-controlled `reinstated` event is allowed only when it restores the
exact same decision:

- the semantic fingerprint is unchanged;
- the previous revocation is referenced explicitly;
- a new impact preview is current;
- technical effects and dependent lifecycles are not assumed to be restored.

Any changed content, condition or constraint requires a new linked proposal.

## Resolved Persistence Direction

Each proposal has one versioned canonical decision-event ledger. Current status
and the human-readable current decision are projections of that ledger. Design
will define the exact path, serialization, event ordering, predecessor links,
hash protection and recovery mechanics, but may replace the single-ledger model
only with explicit technical evidence.

## Resolved Legacy Policy

Migration is loss-aware:

- valid legacy values are preserved;
- missing or malformed fields become `unknown_legacy`;
- source provenance and the original readable value are retained;
- owner, date and rationale are never inferred from Git metadata;
- ambiguous authority emits a diagnostic;
- new decision revisions remain blocked until owner curation resolves the
  ambiguity;
- migration may still preserve the historical record.

## Remaining Design Clarifications

The implementation specification must still determine:

1. the exact ledger schema and stable event identity formula;
2. hash-chain and predecessor validation;
3. atomic replacement, locking, exact-retry and recovery mechanics;
4. the workspace schema transition and compatibility window;
5. the complete downstream consumer inventory and invalidation graph;
6. whether `decision.md` remains generated or is retained as a compatible
   projection maintained by the canonical writer;
7. bounded impact-preview payload and remediation-action ordering.

These are design obligations, not unresolved owner policy decisions.
