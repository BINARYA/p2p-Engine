# Alternatives Considered

## 1. Ignore Placeholder Supplemental Artifacts Entirely

The simplest fix is to drop supplemental artifacts from scoring when their
content is placeholder-only. This solves the observed false negative and keeps
the primary section authoritative.

Tradeoff: it may hide the fact that a supplemental artifact still needs work.
If this option is chosen, the implementation should still allow a separate weak
artifact warning through artifact coverage.

## 2. Score Each Evidence Source Separately, Then Aggregate

This is the preferred option. The primary proposal section and supplemental
artifact are scored independently. Meaningful primary evidence remains
meaningful. Placeholder supplemental evidence can contribute zero additional
value or a warning, but it cannot dominate the aggregate result.

Tradeoff: this is slightly more code than string concatenation, but it matches
how readiness evidence is presented to the user.

## 3. Mark The Execution Plan As Optional For Acceptance Criteria

Another option is to remove `execution-plan.md` from the acceptance criterion
calculation. This eliminates the observed bug for one criterion.

Tradeoff: it treats the symptom in one place and does not fix the general
composed-evidence problem.

## 4. Manually Repair Question State When It Happens

Agents can import corrected `questions.yml` when state and applied markers
disagree.

Tradeoff: this is the workaround used during PROP-095, not a product behavior.
It requires knowledge of internals and conflicts with the rule that `.p2p`
state should be changed through supported primitives.

## 5. Normalize Applied Question State In Reassess Or Summary

This is the preferred direction. If a question has a durable applied marker,
readiness should classify it consistently as closed, or the supported reassess
path should promote it to `state: applied`.

Tradeoff: the implementation must be careful not to classify arbitrary answered
questions as applied. It should require `applied_to_proposal: true` and a
non-empty `applied_at` or equivalent strong marker.

## Selected Direction

Use artifact-aware evidence aggregation for readiness criteria and supported
question-state normalization for already-applied answered questions. Preserve
all existing readiness profile weights and thresholds.
