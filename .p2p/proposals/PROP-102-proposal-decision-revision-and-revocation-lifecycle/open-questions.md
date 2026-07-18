# Open Questions

## Resolved Owner Policy

1. `withdrawn`, `rejected`, `revoked` and `superseded` have distinct meanings;
   `deprecated` is a downstream operational state.
2. Revocation remains available after an impact preview even when dependent
   work exists; remediation is explicit and downstream lifecycles are not
   mutated automatically.
3. `reinstated` may restore only the exact same semantic decision with an
   explicit revocation reference, current impact preview and new owner
   authorization.
4. One versioned decision-event ledger per proposal is the canonical decision
   history source; current status is a projection.
5. Legacy migration preserves unknown or malformed fields as `unknown_legacy`
   with provenance, never infers owner evidence from Git and blocks later
   revision when authority is ambiguous.

## Remaining Design Obligations

These are not unresolved owner policy questions:

1. exact ledger path and serialization;
2. event identity, predecessor and integrity-hash formula;
3. lock, atomic replacement, exact-retry and recovery mechanics;
4. next workspace schema and compatibility-window details;
5. complete downstream consumer and invalidation inventory;
6. current-decision projection format;
7. bounded impact-preview and remediation-action payload;
8. large-history and large-workspace performance ceilings.
