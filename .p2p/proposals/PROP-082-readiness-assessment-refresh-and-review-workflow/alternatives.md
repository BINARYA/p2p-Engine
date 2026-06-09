# Alternatives - PROP-082

## Preferred: artifact-covering interview plus stepped assertiveness

The readiness workflow should generate questions across the whole proposal
artifact set, not only against the missing numeric readiness criteria. Questions
should cover the proposal text and all supporting artifacts that make the
proposal approvable: problem, goals, non-goals, proposal direction, acceptance
criteria, exploration findings, alternatives, tradeoffs, risks, assumptions,
open questions, impact/overlap, readiness evidence, and duplicate/aggregation
candidates.

Answers should be applied back into every useful affected artifact through
available CLI primitives. A single answer may update proposal text, risks,
assumptions, alternatives, open questions, readiness evidence, or impact
artifacts when those artifacts are involved.

Agent assertiveness should be derived from readiness level through a stepped
policy. The lower the readiness, the more the agent must challenge, ask, and
refuse to recommend acceptance. As readiness approaches the target, the agent
should become less intrusive and focus on residual risks or confirmation.

## Alternative: readiness criteria only

The system could generate questions only for missing readiness criteria such as
`risk_coverage` or `alternatives_quality`.

This is insufficient because readiness criteria are a scoring projection, not
the full proposal memory. A proposal can have a missing or stale supporting
artifact even when a criterion label appears covered.

## Alternative: fixed pedantry index

The system could add a dedicated numeric pedantry or assertiveness index.

This is not preferred for the MVP. It introduces another score to calibrate and
explain, while readiness score, failed gates, confidence, missing artifacts, and
question state already provide enough signals to choose agent behavior.

## Alternative: owner-only stop signal

The system could always keep asking until readiness reaches 100 unless the owner
explicitly stops the flow.

This is too aggressive for near-complete proposals. The better behavior is a
stepped policy plus question/group states. The owner can still stop, defer, mute,
or accept with override, but the agent behavior should be proportionate to the
remaining readiness gap.

## Alternative: chat-only application of answers

The agent could ask questions and summarize answers in chat without updating
proposal artifacts.

This is rejected. Readiness and future agents need durable project memory.
Answers must be written back into affected artifacts through public CLI/MCP
write primitives.
