# PROP-089 - Readiness Question-State Convergence

## Status

`draft`

## Problem

Proposal readiness can remain gate-blocked after owner answers are recorded and applied because the assessment mixes structured question state with textual parsing of open-questions.md. In PROP-088, Q001 is applied in questions.yml and reflected in artifacts, but readiness still reports owner_questions_resolution:needs_owner_input and counts open questions from markdown text. This makes readiness feel sticky and can mislead agents and owners about proposal maturity.

## Context

The existing readiness review/question design says evidence-aware assessment should treat resolved open questions and applied answers as evidence for owner-question resolution. The current implementation still derives owner question blockers from count_open_questions(open-questions.md) and only separately checks pending high-priority structured questions. This creates divergent sources of truth between questions.yml and open-questions.md.

## Goals

- Make structured proposal question state the authoritative source for owner-question readiness when questions.yml exists.
- Keep open-questions.md as a human-readable artifact, not the primary lifecycle state for answered/applied questions.
- Make readiness confidence and failed gates reflect priority, state, and application status of structured questions.
- Preserve compatibility for legacy proposals that do not have questions.yml.
- Improve readiness review output so it reports concrete remaining questions instead of a generic sticky gate.

## Non-Goals

- Do not make readiness accept, reject, or defer proposals.
- Do not remove open-questions.md or break existing proposal artifacts.
- Do not turn low- or medium-priority follow-up questions into silent acceptance approval.

## Proposal

Revise evidence-aware readiness assessment so questions.yml is the source of truth for owner-question resolution whenever it exists. Only unresolved structured questions should drive the owner_questions_resolution gate. Applied, retired, superseded, muted, or explicitly deferred questions should not behave like open unanswered questions, though deferred or muted items may reduce confidence or appear as cautions. For legacy proposals without questions.yml, keep the current markdown fallback. Readiness review should list the exact remaining structured questions and distinguish blocking high-priority owner input from residual medium/low follow-up.

## Acceptance Criteria

- When all high-priority proposal questions are answered and applied, readiness no longer keeps owner_questions_resolution failed solely because open-questions.md contains historical answered questions.
- When questions.yml exists, readiness uses question state and priority to determine owner-question blockers.
- Medium/low unanswered questions are surfaced as residual follow-up or confidence cautions, not necessarily as hard failed gates unless policy explicitly says so.
- Legacy proposals without questions.yml continue to use the markdown fallback behavior.
- Readiness review reports the concrete remaining question IDs, priorities, and states.
- Tests cover answered/applied questions, remaining high-priority questions, remaining medium/low questions, deferred/muted questions, and legacy markdown fallback.

## Decision

Pending.
