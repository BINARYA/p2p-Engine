# Exploration - Proposal Decision Revision and Revocation Lifecycle

## Observed Problem

The current decision model stores one visible outcome and rewrites both the
proposal status and `decision.md`. It does not represent a sequence such as:

1. a proposal is accepted and becomes authoritative;
2. implementation or later evidence shows that the decision is wrong;
3. the owner removes its authority;
4. remediation or replacement work follows separately.

Git can recover older bytes, but normal project queries, validation and
decision-context retrieval do not treat Git history as the current semantic
model. Rewriting `accepted` as `rejected` therefore changes the apparent past
instead of recording a later reversal.

## Required Semantic Separation

The lifecycle needs two related but distinct concepts:

- immutable decision events describing what the owner decided at a point in
  time;
- an effective proposal state and authority projection derived from the valid
  event sequence.

An event must record stable identity, proposal identity, outcome, reason,
actor/approver, decision time, previous event, optional replacement lineage,
authority evidence and schema version. Audit timestamps must not determine
semantic identity.

## Confirmed Lifecycle Vocabulary

| State or event | Meaning | Effective authority |
| --- | --- | --- |
| `draft` | No final owner decision exists. | Exploratory |
| `deferred` | Decision postponed; reconsideration remains possible. | Unresolved |
| `rejected` | Proposal was considered but never adopted. | Historical |
| `accepted` | Proposal became an active project decision. | Active |
| `accepted_with_changes` | Qualified acceptance; conditions remain part of authority. | Active and qualified |
| `withdrawn` | An undecided proposal was abandoned by its owner. | Historical, never active |
| `revoked` | A previously accepted decision has been cancelled without claiming rollback. | Historical, previously active |
| `superseded` | A previously effective decision has been replaced through explicit lineage. | Historical; replacement may be active |
| `split` | The original proposal has been replaced by explicit split targets. | Historical lineage |
| `merged_into_other` | The original proposal has been absorbed by an explicit target. | Historical lineage |
| `deprecated` | Continued use is discouraged or time-bounded pending remediation. | Downstream operational state, not a proposal outcome |
| `reinstated` | The exact same revoked decision is restored by the owner. | Returns to the referenced prior active authority |

The owner confirmed that `rejected`, `revoked`, `withdrawn` and `superseded`
are not synonyms and that `deprecated` is not a terminal proposal outcome.

## Transition Principles

- Initial `rejected` is valid only when the proposal has never been active.
- `accepted` and `accepted_with_changes` cannot be rewritten as if they never
  happened.
- Cancellation after acceptance creates a `revoked` event.
- Replacement after acceptance creates a `superseded` event with an explicit
  replacement proposal or decision identity.
- Reinstatement is valid only for the same semantic fingerprint, an explicit
  revocation reference, a current impact preview and new owner authority.
- Changed content, conditions or constraints require a new linked proposal.
- Repeating the exact same owner operation may be idempotent; a conflicting
  retry must fail.
- Invalid transitions fail before any canonical write.
- Reconsideration must create an explicit later event or a linked proposal; it
  must not erase the rejection or revocation.
- Current status is derived from valid event order and cannot disagree with the
  event ledger without a validation diagnostic.

## Downstream Impact Model

Revocation changes decision authority, not physical reality. The system should:

- remove the revoked decision from active project projections;
- retain its rationale and previous active interval as historical context;
- invalidate or refresh derived registries, decision context and next actions;
- flag active Change Sets, Work, specifications and vertical evidence that
  depend on the revoked decision;
- preserve completed implementation evidence;
- require explicit remediation, replacement or rollback work where needed;
- prevent publication and summaries from presenting the revoked decision as
  current;
- avoid automatically changing unrelated owner-controlled lifecycle states.

## Compatibility Direction

Existing workspaces with a single `decision.md` need a deterministic legacy
interpretation. The current decision becomes the first imported event, with
provenance identifying the legacy source. Migration must not invent prior
events, actors, reasons, dates or replacement links. Read compatibility may
precede a governed forward migration, but new event-dependent writes must be
blocked on schemas that cannot preserve the history safely.

Missing or malformed legacy values remain `unknown_legacy` with source
provenance. Ambiguous authority blocks later revision until owner curation but
does not block loss-aware preservation.

## Authority And Safety

Reject, revoke, supersede, withdraw and any future reinstatement remain explicit
owner decisions. CLI and permission-gated MCP must call one domain service and
share transition, preview, consent, stale-check, atomic-write and audit rules.
Managed branch rejection remains a collaboration decision and must not be
confused with proposal-decision rejection.

The owner selected one versioned canonical decision-event ledger per proposal.
Current status and human-readable decision output remain projections.

## Dependency On Future Consolidation

The future thematic memory layer may summarize effective decisions only after
this lifecycle provides stable event identity, current authority, historical
authority and replacement lineage. Consolidation must preserve references to
the source events and expand to them when the summary is stale or ambiguous.
