# Readiness Question-State Convergence

## Provenance

- Proposal: PROP-089
- Source: .p2p/proposals/PROP-089-readiness-question-state-convergence

## Problem

Proposal readiness currently has two competing sources for owner-question state: the structured questions.yml lifecycle and the legacy open-questions.md markdown text. When both exist, readiness can continue to treat stale markdown questions as open even after the corresponding structured questions have been answered and applied.

This creates a false blocker at the per-proposal readiness level. A proposal can show owner_questions_resolution:needs_owner_input even though questions.yml shows that the owner has already answered or resolved the relevant questions. The issue does not affect whole-project readiness directly; it affects the readiness assessment for individual proposals and then propagates misleading next actions to agents and owners.

The impact is practical: agents may keep asking for already-resolved input, owners may see a proposal as less mature than it is, and acceptance decisions may require unnecessary override. The root cause is that readiness still parses open-questions.md as blocking state instead of treating questions.yml as the authoritative lifecycle record whenever structured question state exists.

## Proposal

Revise evidence-aware proposal readiness so questions.yml is the authoritative source for owner_questions_resolution whenever it exists. Blocking owner questions are unresolved structured questions with status to_answer or reopened and high priority by default. A question with status answered must not count as missing owner input; it represents received owner input that still needs application into proposal artifacts or readiness evidence, and should appear as answered_not_applied or residual follow-up until applied. Medium and low unresolved questions are residual follow-up, cautions, or confidence reductions unless a readiness policy explicitly marks them blocking. Applied, retired, and superseded questions are closed for owner-question readiness. Muted and deferred questions are non-blocking; deferred items may reduce confidence or appear as cautions. When questions.yml exists, open-questions.md is narrative evidence only and cannot reopen structured questions. For legacy proposals without questions.yml, keep the current markdown fallback. Readiness explain/review should show blocking_owner_questions, answered_not_applied, residual_follow_up, confidence_notes, and whether markdown fallback was used. Owner override remains valid: the owner may accept or proceed despite unresolved questions, but readiness records the override separately from the computed state; override changes the governance/effective decision status, not the computed readiness truth.

## Decision

# Decision - PROP-089

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted by owner with explicit readiness override after verification: the readiness/question-state convergence behavior is already implemented and validated with focused readiness/question tests, CLI/MCP contract tests, full pytest, and p2p validate. Computed readiness remains partial at 70, but there are no failed gates, missing artifacts, suggested next actions, or eligible owner questions.

## Date

2026-07-02

## Approver

local
