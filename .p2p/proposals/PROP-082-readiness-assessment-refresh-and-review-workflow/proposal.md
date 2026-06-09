# PROP-082 - Readiness Assessment Refresh And Review Workflow

## Status

`accepted`

## Problem

The current proposal readiness CLI can bootstrap and refresh readiness snapshots, but it does not provide a governed way to qualitatively reassess an updated proposal, confirm that owner questions have been resolved, raise confidence, update criterion scores, clear failed gates, or import and review an evidence-based assessment. As seen with earlier accepted proposals, a proposal can become substantively ready for decision while p2p proposal readiness refresh still keeps a conservative bootstrap score, forcing acceptance to rely on owner override even when the artifacts are actually mature. The deeper issue is that readiness currently mixes two distinct capabilities. First, P2P must store enough exhaustive, inspectable information to judge proposal quality: artifacts, evidence, scores, missing items, gates, confidence, audit notes, unresolved owner questions, question state, and aggregation candidates. Second, P2P must guide the agent behavior that uses that information: the agent must be explicitly told to be proactive, pedantic, skeptical of thin artifacts, willing to ask owner questions, and unwilling to recommend acceptance when methodological gaps remain. Storing complete information is necessary but not sufficient. Without explicit agent behavioral guidance, an agent can read complete state and still behave passively, summarize gaps without challenging them, or treat a mechanically valid proposal as decision-ready. Without deterministic question-and-answer memory, the agent cannot reliably conduct an interview, track which gaps have been resolved, decide whether to re-ask, defer, or mute questions, detect proposal overlap during the interview, or use owner answers to refine the proposal.

## Context

This proposal refines the accepted exploration and readiness direction by separating information completeness from agent behavioral guidance. It keeps agent proactivity and deterministic clarification interview inside PROP-082 for now rather than splitting a separate proposal. It should remain compatible with conservative deterministic refresh, owner-controlled governance, readiness profiles, evidence records, p2p next recommendations, MCP context, clarification workflows, and agent skills. It should also connect proposal-level readiness with project-level assessment and maturity rubrics without collapsing them into one score. Current CLI primitives can add contributions, update structured proposal sections, and generate/import clarification prompts, but a production-ready workflow requires a first-class deterministic proposal-question object and CLI surface. Backward compatibility is mandatory: older proposals without question state must continue to work, with CLI commands reporting absent question state rather than failing.

## Goals

- Separate information completeness from agent behavioral guidance in the readiness model.
- Provide a governed assess/review path that can update evidence, criterion scores, confidence, missing items, gates, suggested next actions, unresolved owner questions, and overlap candidates after proposal artifacts change.
- Introduce a first-class deterministic clarification interview memory for low-readiness proposals: generated questions start with empty answers, answers are recorded as the interview progresses, and every question remains tied to the readiness gap it is meant to resolve.
- Make agent guidance operational and proactive by default: agents must challenge thin or incomplete artifacts, ask focused owner questions one at a time, reassess the question list after each answer, propose alternatives and tradeoffs, detect mergeable proposals, and avoid recommending acceptance when readiness is methodologically weak.
- Define production-ready CLI commands and data structures for question lifecycle, answer recording, deferral, muting, grouping, applying answers, and handling merge candidates.
- Allow the agent to use completed question-and-answer memory to refine the proposal through supported CLI tools.
- Preserve owner control: agent proactivity may recommend, question, assess, and prepare aggregation, but must not decide acceptance, rejection, deferral, aggregation closure, or override.
- Preserve backward compatibility for proposals that have no question/interview state yet.

## Non-Goals

- Do not make agents autonomous governance decision makers.
- Do not overwrite computed readiness scores with owner override outcomes.
- Do not require every small proposal to receive heavyweight qualitative review or a full interview.
- Do not replace deterministic refresh. Refresh remains a conservative synchronization step, while assess/review is the evidence-aware path.
- Do not store interview state only in free-form chat memory or only as unstructured contributions.
- Do not break existing proposals, registries, readiness snapshots, or CLI inspection commands when question state is absent.

## Proposal

Extend the readiness review and proposal-question workflow so generated questions are artifact-aware, not only score-gap-aware. When readiness is weak, low-confidence, blocked by gates, or missing evidence, the agent must inspect the full proposal artifact set and generate or update questions that seek coverage across proposal.md, exploration.md, findings.md, alternatives.md, risks.md, assumptions.md, open-questions.md, suggested-scope.md, impact-map.yml, related/conflict artifacts, readiness.yml, questions.yml, and duplicate or aggregation evidence. The question list should represent the missing information needed to make the proposal robust and approvable, not just the labels currently listed in readiness.missing. When answers are recorded, the workflow must help the agent apply them to every useful affected artifact through available CLI or MCP write primitives. A question answer may update the proposal text, acceptance criteria, alternatives, tradeoffs, risks, assumptions, open questions, impact analysis, duplicate/aggregation notes, or readiness evidence. Applied question state should mean the answer has been propagated into proposal artifacts or an explicit reason exists for why no artifact update was needed. Agent assertiveness should be driven by a stepped readiness policy rather than a separate pedantry score. Very low or weak readiness requires proactive challenge, next-question selection, and refusal to recommend acceptance without owner override. Partial readiness requires focused follow-up on missing artifacts and high-risk ambiguity. Near-target readiness requires only residual high-value questions or confirmation. Deferred and muted question/group states reduce re-asking unless the owner explicitly asks to increase readiness or revisit unanswered material. After applying answers or importing refined artifacts, readiness must be recalculated through the evidence-aware assessment path; low readiness should cause the skill to direct the agent to continue interviewing the owner instead of passively reporting gaps.

## Acceptance Criteria

- Readiness review generates or updates questions that seek coverage across the full proposal artifact set, not only missing readiness criterion names.
- Question answers can be mapped to multiple affected artifacts, and apply behavior reports which artifacts should be updated or why no update is needed.
- Agent guidance defines stepped assertiveness from readiness score, label, failed gates, confidence, missing evidence, and question state rather than a standalone pedantry index.
- When readiness is weak, low-confidence, or gate-blocked, agent guidance requires the agent to initialize/update questions, ask the next focused question, record the answer, apply it, and recalculate readiness.
- Muted and deferred question or group states reduce re-asking by default while still allowing the owner to explicitly revisit them to increase readiness.
- Readiness recalculation after artifact refinement updates missing criteria, failed gates, confidence, suggested next actions, and acceptance cautions using current artifact evidence.
- Existing owner authority remains intact: agents may challenge, recommend, and prepare artifact updates, but cannot accept, reject, defer, merge, or aggregate proposals without owner-controlled governance actions.

## Decision

Pending.
