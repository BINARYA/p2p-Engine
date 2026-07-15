# Alternatives

## Stateless Review Improvements

Rejected because messages alone cannot preserve answers, lifecycle or answered-versus-applied state across sessions.

## Questions Embedded In Project Definition

Rejected because interview state would share authority and hash churn with applied definition truth.

## Synthetic Project Proposal

Rejected because it conflates project-definition convergence with proposal governance.

## Sequential Definition And Question Writes

Rejected because compensating rollback cannot provide the same invariant as one validated multi-target transaction.

## Add Only A v1-to-v2 Registry Entry

Rejected because the current compatibility planner still renders legacy bootstrap operations. Each adjacent transition requires an owning handler.

## Preserve Legacy Questions As A Parallel Writable Authority

Rejected because two writable sources require last-write-wins or bidirectional synchronization. After v2 migration the dedicated artifact is authoritative.

## Infer Legacy Answered Or Applied State

Rejected because absence of an open question is not evidence that an owner answered or applied it.

## Blindly Reject Every Reused Token

Rejected because an apply response lost after a successful commit must be recoverable. Exact retry returns `already_applied`; changed replay is rejected.

## Clock Expiry Without Preview Receipts

Rejected because a stateless deterministic token has no reliable issued-at or consumption history. Time expiry requires a separate explicit receipt contract.

## Automatic Vertical Remapping

Rejected because text similarity cannot safely move owner answers to a changed semantic target. Declarative aliases or explicit owner action are required.

## Automatic Derived Rebuild

Rejected because deterministic refresh, agent curation, publication and owner review have separate lifecycle results and failure boundaries.
