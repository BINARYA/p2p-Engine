# Findings

```yaml
findings:
  - id: F001
    type: data_integrity
    title: Current decisions are overwrite-shaped rather than event-shaped
    impact: critical
    related_to:
      - PROP-019
      - PROP-077
  - id: F002
    type: hidden_decision
    title: Rejection before adoption and reversal after adoption require different semantics
    impact: high
    related_to:
      - PROP-091
      - PROP-100
  - id: F003
    type: architectural_implication
    title: Effective status should be derived from immutable decision events
    impact: high
    related_to:
      - PROP-010
      - PROP-016
      - PROP-100
  - id: F004
    type: consistency_risk
    title: Proposal status and decision artifact are currently written independently
    impact: high
    related_to:
      - PROP-053
      - PROP-101
  - id: F005
    type: downstream_impact
    title: Revocation changes authority but does not roll back implemented behavior
    impact: high
    related_to:
      - PROP-015
      - PROP-079
      - PROP-094
  - id: F006
    type: compatibility_migration
    title: Existing single-decision artifacts need loss-aware legacy import
    impact: high
    related_to:
      - PROP-095
      - PROP-097
      - PROP-101
  - id: F007
    type: scope_boundary
    title: Managed branch rejection is distinct from proposal decision rejection
    impact: medium
    related_to:
      - PROP-066
      - PROP-072
      - PROP-075
  - id: F008
    type: future_dependency
    title: Thematic memory consolidation depends on stable lifecycle authority and lineage
    impact: high
    related_to:
      - PROP-100
  - id: F009
    type: owner_policy
    title: Revocation remains available after impact preview without automatic downstream lifecycle mutation
    impact: high
    related_to:
      - PROP-079
      - PROP-094
  - id: F010
    type: architecture_decision
    title: One versioned decision-event ledger per proposal is the canonical history source
    impact: high
    related_to:
      - PROP-010
      - PROP-101
  - id: F011
    type: compatibility_policy
    title: Unknown legacy evidence is preserved without inference and blocks later revision when authority is ambiguous
    impact: high
    related_to:
      - PROP-095
      - PROP-097
```
