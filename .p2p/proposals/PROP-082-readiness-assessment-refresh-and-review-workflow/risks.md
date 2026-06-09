# Risks - PROP-082

## Agent becomes annoying instead of useful

If assertiveness is too high after the proposal is already nearly complete, the
owner may experience the agent as obstructive.

Mitigation: use a stepped behavior tied to readiness bands, failed gates,
confidence, and question state. Near target readiness, the agent should ask only
high-value residual questions.

## Agent stays passive when readiness is low

If the skill only reports gaps and does not require next-question behavior, the
agent may summarize problems without driving the interview.

Mitigation: when readiness is low or blocked, agent guidance must require the
agent to initialize/update question memory, select the highest-impact next
question, ask one question at a time, and record answers.

## Questions cover only score gaps, not real artifacts

Generated questions may overfit the readiness criterion names and miss stale
supporting artifacts.

Mitigation: the question generator must inspect and cover the whole proposal
artifact set: proposal.md, exploration artifacts, impact artifacts, readiness,
questions, and duplicate/aggregation evidence.

## Answers remain disconnected from proposal state

Owner answers can be recorded in `questions.yml` but never applied to the
proposal artifacts that should change.

Mitigation: answer application must identify affected artifacts and update all
useful artifacts through available CLI import/update commands. Applied state
should mean that the answer has been propagated, not merely recorded.

## Readiness stays stale after refinement

The system may update artifacts but leave readiness score, missing criteria, or
confidence unchanged.

Mitigation: after applying answers or importing refined artifacts, the workflow
must recompute readiness through the evidence-aware reassessment path and report
remaining gaps. `refresh` should not masquerade as reassessment if it is only
snapshot synchronization.

## Owner control is bypassed

An aggressive agent may treat readiness improvement as authorization to accept,
merge, close, or aggregate proposals.

Mitigation: agent behavior may recommend and prepare, but owner-controlled
governance actions remain explicit decisions.
