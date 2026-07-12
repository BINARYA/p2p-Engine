---
change_id: CHANGE-067
title: Readiness Question-State Convergence
status: completed
created_at: '2026-07-08'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-089
  accepted_decisions: []
implementation_targets:
- local_cli
spec_targets:
- p2p_spec
export_targets:
- openspec
- speckit
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-067 - Readiness Question-State Convergence

## Summary

Revise evidence-aware proposal readiness so questions.yml is the authoritative source for owner_questions_resolution whenever it exists. Blocking owner questions are unresolved structured questions with status to_answer or reopened and high priority by default. A question with status answered must not count as missing owner input; it represents received owner input that still needs application into proposal artifacts or readiness evidence, and should appear as answered_not_applied or residual follow-up until applied. Medium and low unresolved questions are residual follow-up, cautions, or confidence reductions unless a readiness policy explicitly marks them blocking. Applied, retired, and superseded questions are closed for owner-question readiness. Muted and deferred questions are non-blocking; deferred items may reduce confidence or appear as cautions. When questions.yml exists, open-questions.md is narrative evidence only and cannot reopen structured questions. For legacy proposals without questions.yml, keep the current markdown fallback. Readiness explain/review should show blocking_owner_questions, answered_not_applied, residual_follow_up, confidence_notes, and whether markdown fallback was used. Owner override remains valid: the owner may accept or proceed despite unresolved questions, but readiness records the override separately from the computed state; override changes the governance/effective decision status, not the computed readiness truth.

## Rationale

The owner may still decide or accept a proposal with unresolved questions by explicit override. Readiness must report the computed state truthfully and must not pretend unresolved questions are solved. The agent question flow should remain incremental: agents continue to ask the next eligible question one at a time from structured question state.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Change Set metadata.

## Acceptance Criteria

- Change Set metadata is present and reviewable.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
