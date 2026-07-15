# Findings

```yaml
findings:
  - id: F001
    type: capability_gap
    title: Readiness review has no convergence lifecycle
    impact: high
    related_to: [PROP-085, PROP-090]
  - id: F002
    type: incomplete_question_coverage
    title: Required incomplete sections can produce no applicable question
    impact: high
    related_to: [PROP-085]
  - id: F003
    type: orchestration_gap
    title: Managed next actions omit current project-definition gaps
    impact: high
    related_to: [PROP-079]
  - id: F004
    type: usability_and_budget
    title: Unmapped legacy proposal output is unbounded and unprioritized
    impact: medium
    related_to: [PROP-055, PROP-100]
  - id: F005
    type: atomicity_gap
    title: Existing definition apply is single-target and cannot directly commit question state
    impact: critical
    related_to: [PROP-090, PROP-097]
  - id: F006
    type: hidden_decision
    title: Project-question canonical authority and legacy fallback must be explicit
    impact: high
    related_to: [PROP-089, PROP-090, PROP-096]
  - id: F007
    type: migration_architecture_gap
    title: Current compatibility planner is specialized for legacy-to-v1 rather than transition handlers
    impact: critical
    related_to: [PROP-095, PROP-097]
  - id: F008
    type: migration_semantics_gap
    title: Legacy definition questions lack deterministic v2 identity and lifecycle mapping
    impact: critical
    related_to: [PROP-090, PROP-095]
  - id: F009
    type: authority_gap
    title: Answer and lifecycle mutations require an operation-level role and consent matrix
    impact: critical
    related_to: [PROP-089, PROP-091, PROP-096]
  - id: F010
    type: replay_semantics_gap
    title: Existing deterministic preview tokens do not define expiry consumption or exact committed retry
    impact: high
    related_to: [PROP-090, PROP-097]
  - id: F011
    type: vertical_reconciliation_gap
    title: Lock drift detection does not define question identity revision and retirement behavior
    impact: high
    related_to: [PROP-085, PROP-090]
  - id: F012
    type: source_of_truth
    title: Unapplied project answers must remain inactive in decision context
    impact: high
    related_to: [PROP-100]
  - id: F013
    type: pagination_consistency
    title: Stable ordering requires cursors bound to a readiness snapshot
    impact: medium
    related_to: [PROP-055, PROP-100]
  - id: F014
    type: compatibility_decision
    title: Schema v1 requires operation-level compatibility gates and an explicit upgradeable status
    impact: high
    related_to: [PROP-095, PROP-097]
  - id: F015
    type: source_of_truth
    title: Answered questions remain distinct from applied definition and owner decisions
    impact: high
    related_to: [PROP-089, PROP-091]
  - id: F016
    type: integration_boundary
    title: Progress and freshness consume convergence without becoming alternative readiness engines
    impact: high
    related_to: [PROP-090, PROP-100]
  - id: F017
    type: performance_contract
    title: Scale acceptance needs source-access and payload budgets rather than a vague timing test
    impact: medium
    related_to: [PROP-055, PROP-100]
  - id: F018
    type: pilot_constraint
    title: Repository-specific readiness gaps are evidence not generic policy
    impact: medium
    related_to: [PROP-101]
```

The principal architectural requirement is one owner for every state transition. Schema, question lifecycle, definition truth, decision authority and derived projections must remain separate even though convergence orchestrates them.
