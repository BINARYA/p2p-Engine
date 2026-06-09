# Assumptions - PROP-082

## Readiness is the main behavior signal

The system does not need a separate pedantry score in the MVP. Agent
assertiveness can be derived from readiness score, label, failed gates,
confidence, missing criteria, unanswered questions, and question/group state.

## Stepped assertiveness is sufficient

The agent can follow readiness bands:

- very low readiness: strongly proactive, challenge assumptions, ask the next
  blocking question, and avoid acceptance recommendations;
- partial readiness: continue the interview, focus on missing artifacts and
  high-risk ambiguity;
- near target readiness: ask only residual high-value questions or request
  confirmation;
- owner-muted or explicitly deferred areas: do not re-ask by default unless the
  owner asks to increase readiness or revisit muted/deferred questions.

## Question state replaces a dedicated "stop working on this" index

The existing question and group states can represent owner intent:

- `to_answer`: keep asking when relevant;
- `defer`: skip for now, keep available;
- `muted`: skip by default unless explicitly revisited;
- `answered` and `applied`: use the answer to refine artifacts;
- `retired` and `superseded`: preserve history without re-asking obsolete
  questions.

## Answers may affect multiple artifacts

A single owner answer can legitimately update proposal text, acceptance
criteria, alternatives, risks, assumptions, open questions, impact analysis, or
readiness evidence. Application should be artifact-aware rather than
one-question-to-one-file.

## Low readiness requires agent initiative

When readiness is low, failed, or low-confidence, the skill should instruct the
agent to take initiative: inspect gaps, update questions, ask the next focused
question, and record the answer. The agent should not wait for the owner to ask
what to do next.
