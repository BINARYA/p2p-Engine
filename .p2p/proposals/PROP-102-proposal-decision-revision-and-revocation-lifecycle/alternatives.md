# Alternatives

## A. Keep Current Overwrite Model And Rely On Git

Continue replacing `decision.md` and proposal status, and use Git history when
an earlier decision must be reconstructed.

Benefits:

- no schema or command changes;
- minimal implementation cost.

Costs and risks:

- ordinary project memory loses visible decision history;
- retrieval and derived artifacts cannot reason about prior authority;
- state can diverge after partial writes;
- consolidation can summarize the wrong current or historical meaning.

Assessment: reject. Git auditability is not a queryable lifecycle model.

## B. Require A New Corrective Proposal For Every Reversal

Keep accepted proposals immutable and require a new proposal to explain that an
old decision should no longer apply.

Benefits:

- preserves the original proposal and decision;
- creates explicit rationale for corrective work;
- requires little change to existing decision storage.

Costs and risks:

- the old proposal remains marked active unless another authority mechanism
  deactivates it;
- every consumer must infer that the corrective proposal cancels the original;
- a reversal without replacement is awkward;
- relation omissions can leave contradictory active decisions.

Assessment: useful as a remediation pattern, but insufficient as the lifecycle
authority model.

## C. Append-Only Decision Events With Derived Effective State

Record every owner decision as an immutable event and derive current proposal
status and authority from a validated transition sequence.

Benefits:

- preserves historical truth and reasons;
- supports rejection, revocation, replacement and reconsideration explicitly;
- provides stable input for retrieval and future consolidation;
- enables deterministic validation and impact diagnostics.

Costs and risks:

- introduces a versioned schema and migration;
- requires updates across several downstream consumers;
- needs atomic multi-artifact replacement and concurrency handling.

Assessment: recommended.

## D. Store Individual Immutable Event Files Plus A Manifest

Create one file per event and maintain a manifest that identifies order and the
current head.

Benefits:

- individual corruption can be isolated;
- event files are independently readable.

Costs and risks:

- manifest and event files can diverge;
- ordering and atomic multi-file replacement are more complex;
- directory and migration overhead is unnecessary for the expected low event
  volume per proposal.

Assessment: not selected. The owner selected one versioned canonical
decision-event ledger per proposal, with current state maintained as a separate
projection.
