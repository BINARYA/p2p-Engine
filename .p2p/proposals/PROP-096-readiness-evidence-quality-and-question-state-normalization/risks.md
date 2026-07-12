# Risks

## Readiness Becomes Too Optimistic

If supplemental placeholders are ignored too broadly, readiness may stop
surfacing useful weak-artifact signals.

Mitigation: keep placeholder detection strict for primary evidence, and surface
weak supplemental artifacts through artifact coverage or criterion evidence
notes where appropriate.

## Applied Question Normalization Masks Real Work

If normalization treats any answered question as applied, owner follow-up could
be lost.

Mitigation: normalize only when the durable applied marker is present, such as
`applied_to_proposal: true` plus `applied_at`.

## Existing Readiness Scores Shift Unexpectedly

Changing evidence aggregation can affect score outputs for existing proposals.

Mitigation: limit the change to composed evidence cases where meaningful
primary evidence is combined with placeholder-only supplemental evidence. Add
regression tests for unchanged missing and placeholder-only behavior.

## Direct State Repair Becomes Normalized

The observed workaround involved importing a corrected question state. That
should not become the ordinary user workflow.

Mitigation: implement the behavior in readiness/question services and expose it
through existing reassess/apply paths rather than documenting direct YAML edits.

## Artifact Coverage And Readiness Disagree

A supplemental artifact can remain weak while the criterion is satisfied from
primary evidence.

Mitigation: report those as separate concepts. Criterion quality can be
meaningful while artifact coverage still suggests improving the supplemental
artifact.
