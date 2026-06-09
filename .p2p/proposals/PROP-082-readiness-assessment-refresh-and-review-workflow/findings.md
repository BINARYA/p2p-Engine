# Findings - PROP-082

## F001 - PROP-006 Exposed A Real Workflow Gap

PROP-006 was refined enough for owner acceptance, but readiness remained at the
conservative bootstrap score after `p2p proposal readiness refresh`.

Impact:
Readiness needs a public reassessment primitive, otherwise mature proposals may
look artificially weak.

## F002 - Refresh And Assess Are Different Operations

`refresh` should not imply qualitative judgment unless it actually re-evaluates
criteria and evidence.

Impact:
The CLI should use explicit language so users understand whether a command is
synchronizing a snapshot or changing analytical readiness.

## F003 - Owner Override Is Not A Substitute For Assessment

Owner override is appropriate when the owner intentionally accepts below target
readiness. It is not the right mechanism for saying that the computed assessment
is stale.

Impact:
The model needs assessment review in addition to override.

## F004 - Questions Must Cover Proposal Artifacts, Not Only Scores

Readiness criteria are useful, but the proposal is made of multiple artifacts.
Questions should inspect and cover all artifacts that make the proposal robust:
proposal text, exploration, findings, alternatives, risks, assumptions, open
questions, impact, readiness, and duplicate/aggregation evidence.

Impact:
Question generation should be artifact-aware and able to create questions for
stale, missing, placeholder, contradictory, or thin artifacts even if the
readiness criterion name is not itself missing.

## F005 - Applying Answers Must Update All Affected Artifacts

Recording an answer in question memory is not enough. The system must help the
agent propagate answers into the proposal artifacts involved by the answer.

Impact:
`questions apply` or the surrounding agent workflow should produce an
artifact-update plan and use available CLI import/update primitives to update
proposal text, exploration artifacts, impact artifacts, readiness evidence, and
open questions when affected.

## F006 - Pedantry Can Be A Stepped Behavior, Not A New Score

A dedicated pedantry index would add calibration complexity. Readiness bands,
failed gates, confidence, missing criteria, and question state already provide
strong behavior signals.

Impact:
Agent guidance should define stepped assertiveness: high when readiness is low,
focused when readiness is partial, residual when near target, and quiet for
muted/deferred areas unless the owner explicitly reopens them.
