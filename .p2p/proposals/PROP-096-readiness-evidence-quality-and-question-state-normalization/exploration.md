# Exploration - PROP-096

## Observed Failure

During PROP-095 readiness finalization, the proposal had meaningful Acceptance
Criteria in `proposal.md`, but readiness still reported
`acceptance_criteria_quality` as placeholder because the composed evidence also
included `execution-plan.md`, whose entire content was the default placeholder
line.

The same session exposed a second state-normalization problem in
`questions.yml`: some questions had already been marked `applied_to_proposal:
true` with `applied_at` set, but their `state` remained `answered`. The
question apply command skipped them because they were already marked applied,
while readiness still reported them as `answered_not_applied` because it looked
at the state field.

Both defects are small, but they damage trust in readiness because the user sees
missing work even after the underlying evidence has been supplied.

## Intended Fix Shape

The fix should be local to readiness evidence aggregation and proposal question
state normalization.

For composed evidence, readiness should evaluate primary and supplemental
evidence separately before deciding the aggregate quality. A placeholder-only
supplemental artifact can be ignored for scoring or reported as a weak
supplement, but it must not override meaningful primary evidence.

For question state, a record that is internally marked as applied should not be
reported as an unapplied answer. The implementation may either normalize the
state during reassessment or classify such records as closed when summarizing
owner question state.

## Boundary

This is a bug fix, not a new readiness policy. It should keep the existing
profile weights, labels, thresholds, CLI commands, and governance semantics.

The fix must preserve the useful warning behavior for genuinely missing or
placeholder-only evidence.
