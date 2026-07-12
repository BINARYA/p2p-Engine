# Execution Plan - PROP-096

## Implementation Sequence

1. Add regression coverage for composed readiness evidence where the primary
   proposal section is meaningful and a supplemental artifact contains only the
   default placeholder line.
2. Refactor readiness evidence quality evaluation so primary and supplemental
   evidence are assessed independently before aggregation.
3. Ensure a placeholder-only supplemental artifact can contribute no useful
   evidence or a separate warning, but cannot downgrade meaningful primary
   evidence to `placeholder`.
4. Add regression coverage for a proposal question with `state: answered`,
   `applied_to_proposal: true`, and `applied_at` set.
5. Implement deterministic normalization for that question state through the
   supported question reassess/apply/import path, without making manual `.p2p`
   edits part of normal operation.
6. Verify that ordinary answered unapplied questions still flow through the
   existing `p2p proposal questions apply` behavior.
7. Run focused readiness and proposal question tests, then run project
   validation.

## Delivery Boundary

The fix is complete when readiness no longer reports false missing evidence for
meaningful primary sections and no longer reports already-applied answered
questions as pending application, while preserving current readiness profiles,
thresholds, and owner governance semantics.
