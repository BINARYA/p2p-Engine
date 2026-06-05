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
readiness. It is not the right mechanism for saying that the computed
assessment is stale.

Impact:
The model needs assessment review in addition to override.

