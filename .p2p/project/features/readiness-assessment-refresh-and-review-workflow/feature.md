# Readiness Assessment Refresh And Review Workflow

## Provenance

- Proposal: PROP-082
- Source: .p2p/proposals/PROP-082-readiness-assessment-refresh-and-review-workflow

## Problem

The current proposal readiness CLI can bootstrap and refresh readiness snapshots, but it does not provide a governed way to qualitatively reassess an updated proposal, confirm that owner questions have been resolved, raise confidence, update criterion scores, clear failed gates, or import and review an evidence-based assessment. As seen with earlier accepted proposals, a proposal can become substantively ready for decision while p2p proposal readiness refresh still keeps a conservative bootstrap score, forcing acceptance to rely on owner override even when the artifacts are actually mature. The deeper issue is that readiness currently mixes two distinct capabilities. First, P2P must store enough exhaustive, inspectable information to judge proposal quality: artifacts, evidence, scores, missing items, gates, confidence, audit notes, unresolved owner questions, question state, and aggregation candidates. Second, P2P must guide the agent behavior that uses that information: the agent must be explicitly told to be proactive, pedantic, skeptical of thin artifacts, willing to ask owner questions, and unwilling to recommend acceptance when methodological gaps remain. Storing complete information is necessary but not sufficient. Without explicit agent behavioral guidance, an agent can read complete state and still behave passively, summarize gaps without challenging them, or treat a mechanically valid proposal as decision-ready. Without deterministic question-and-answer memory, the agent cannot reliably conduct an interview, track which gaps have been resolved, decide whether to re-ask, defer, or mute questions, detect proposal overlap during the interview, or use owner answers to refine the proposal.

## Proposal

Extend the readiness review and proposal-question workflow so generated questions are artifact-aware, not only score-gap-aware. When readiness is weak, low-confidence, blocked by gates, or missing evidence, the agent must inspect the full proposal artifact set and generate or update questions that seek coverage across proposal.md, exploration.md, findings.md, alternatives.md, risks.md, assumptions.md, open-questions.md, suggested-scope.md, impact-map.yml, related/conflict artifacts, readiness.yml, questions.yml, and duplicate or aggregation evidence. The question list should represent the missing information needed to make the proposal robust and approvable, not just the labels currently listed in readiness.missing. When answers are recorded, the workflow must help the agent apply them to every useful affected artifact through available CLI or MCP write primitives. A question answer may update the proposal text, acceptance criteria, alternatives, tradeoffs, risks, assumptions, open questions, impact analysis, duplicate/aggregation notes, or readiness evidence. Applied question state should mean the answer has been propagated into proposal artifacts or an explicit reason exists for why no artifact update was needed. Agent assertiveness should be driven by a stepped readiness policy rather than a separate pedantry score. Very low or weak readiness requires proactive challenge, next-question selection, and refusal to recommend acceptance without owner override. Partial readiness requires focused follow-up on missing artifacts and high-risk ambiguity. Near-target readiness requires only residual high-value questions or confirmation. Deferred and muted question/group states reduce re-asking unless the owner explicitly asks to increase readiness or revisit unanswered material. After applying answers or importing refined artifacts, readiness must be recalculated through the evidence-aware assessment path; low readiness should cause the skill to direct the agent to continue interviewing the owner instead of passively reporting gaps.

## Decision

# Decision - PROP-082

## Status

`accepted`

## Outcome

accepted

## Reason

Owner confirms the refined second-slice direction for artifact-aware proposal questions, stepped readiness-driven agent assertiveness, evidence-aware readiness recalculation, and proactive low-readiness interview behavior.

## Date

2026-06-08

## Approver

owner
