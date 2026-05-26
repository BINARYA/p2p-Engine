---
change_id: CHANGE-009
title: Next Action Recommender MVP
status: completed
created_at: '2026-05-25'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-023
  accepted_decisions: []
implementation_targets:
- local_cli
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-009 - Next Action Recommender MVP

## Summary

Implement an advisory next-action recommender. The command should prefer imported next-actions.yml, fall back to deterministic project state checks, support --top N, and project status should summarize whether an operational brief exists plus the first suggested action.

## Rationale

The owner decided that p2p next should be top-level, advisory only, list ordered actions with --top support, read .p2p/project/next-actions.yml when present, and compute conservative fallback actions when it is missing or empty.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Top-level `p2p next` advisory command.
- `--top` limiting for next-action output.
- Conservative fallback recommender when `next-actions.yml` is missing or empty.
- Operational summary section in `p2p project status`.
- Updated P2P skill guidance.

## Acceptance Criteria

- `p2p next` lists ordered advisory actions from `.p2p/project/next-actions.yml`.
- `p2p next --top 1` shows only the first action.
- `p2p next` falls back to project-state checks without modifying state.
- `p2p project status` reports brief availability, next-action count, and first next action.
- Tests cover stored and fallback next-action behavior.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
