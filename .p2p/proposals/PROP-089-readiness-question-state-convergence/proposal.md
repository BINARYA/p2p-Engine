# PROP-089 - Readiness Question-State Convergence

## Status

`draft`

## Problem

Proposal readiness currently has two competing sources for owner-question state: the structured questions.yml lifecycle and the legacy open-questions.md markdown text. When both exist, readiness can continue to treat stale markdown questions as open even after the corresponding structured questions have been answered and applied.

This creates a false blocker at the per-proposal readiness level. A proposal can show owner_questions_resolution:needs_owner_input even though questions.yml shows that the owner has already answered or resolved the relevant questions. The issue does not affect whole-project readiness directly; it affects the readiness assessment for individual proposals and then propagates misleading next actions to agents and owners.

The impact is practical: agents may keep asking for already-resolved input, owners may see a proposal as less mature than it is, and acceptance decisions may require unnecessary override. The root cause is that readiness still parses open-questions.md as blocking state instead of treating questions.yml as the authoritative lifecycle record whenever structured question state exists.

## Context

The owner may still decide or accept a proposal with unresolved questions by explicit override. Readiness must report the computed state truthfully and must not pretend unresolved questions are solved. The agent question flow should remain incremental: agents continue to ask the next eligible question one at a time from structured question state.

## Goals

- Make questions.yml authoritative for owner-question readiness whenever structured question state exists.
- Keep open-questions.md as human-readable evidence and legacy fallback, not as a competing source of blocking state.
- Preserve the one-question-at-a-time owner interaction flow.
- Keep owner override explicit and auditable when the owner decides despite unresolved questions or partial readiness.

## Non-Goals

- Do not change whole-project readiness semantics.
- Do not remove open-questions.md or require migration of all legacy proposals in this change.
- Do not force the owner to answer every question before making a governance decision.
- Do not turn agent questioning into a batch questionnaire.

## Proposal

Revise evidence-aware proposal readiness so questions.yml is the authoritative source for owner_questions_resolution whenever it exists. Blocking owner questions are unresolved structured questions with status to_answer or reopened and high priority by default. A question with status answered must not count as missing owner input; it represents received owner input that still needs application into proposal artifacts or readiness evidence, and should appear as answered_not_applied or residual follow-up until applied. Medium and low unresolved questions are residual follow-up, cautions, or confidence reductions unless a readiness policy explicitly marks them blocking. Applied, retired, and superseded questions are closed for owner-question readiness. Muted and deferred questions are non-blocking; deferred items may reduce confidence or appear as cautions. When questions.yml exists, open-questions.md is narrative evidence only and cannot reopen structured questions. For legacy proposals without questions.yml, keep the current markdown fallback. Readiness explain/review should show blocking_owner_questions, answered_not_applied, residual_follow_up, confidence_notes, and whether markdown fallback was used. Owner override remains valid: the owner may accept or proceed despite unresolved questions, but readiness records the override separately from the computed state; override changes the governance/effective decision status, not the computed readiness truth.

## Acceptance Criteria

- Given a proposal with questions.yml, owner_questions_resolution is computed from structured question state rather than parsing open-questions.md as a competing blocker.
- A high-priority question with status to_answer or reopened blocks owner_questions_resolution by default.
- A high-priority question with status answered does not block as missing owner input; readiness explain reports it as answered_not_applied or residual follow-up until applied.
- Medium or low unresolved questions appear as residual follow-up, cautions, or confidence notes unless policy marks them blocking.
- Questions in applied, retired, or superseded state are closed for owner-question readiness and do not count as open unanswered blockers.
- Questions in muted or deferred state do not count as open unanswered blockers; deferred questions may reduce confidence or appear as cautions.
- For proposals without questions.yml, the existing open-questions.md markdown fallback still works.
- p2p proposal readiness explain identifies exact blocking structured questions and distinguishes them from answered_not_applied, residual follow-up, and confidence notes.
- Owner acceptance with unresolved questions remains possible only as an explicit override/audit condition; computed readiness remains truthful and is not rewritten to resolved by the override.
- The next-question workflow remains one question at a time and is not changed into a batch interaction.

## Decision

Pending.
