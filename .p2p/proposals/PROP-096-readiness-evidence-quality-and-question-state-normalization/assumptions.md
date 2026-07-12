# Assumptions

- Readiness profile weights, labels, and thresholds should remain unchanged.
- `proposal.md` sections are primary evidence for their matching criteria.
- Supplemental artifacts such as `execution-plan.md` can strengthen evidence,
  but they should not invalidate meaningful primary evidence.
- Placeholder detection is still valuable and should remain strict when the
  primary evidence is absent or placeholder-only.
- `applied_to_proposal: true` with a non-empty `applied_at` is strong enough to
  classify a question as already applied for readiness purposes.
- Existing `p2p proposal questions apply` behavior should remain valid for
  answered questions that are not yet applied.
- The fix can be implemented with focused service tests and does not require a
  broad redesign of the proposal artifact model.
