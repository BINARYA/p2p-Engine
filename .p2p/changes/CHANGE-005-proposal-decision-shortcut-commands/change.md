---
change_id: CHANGE-005
title: Proposal Decision Shortcut Commands
status: completed
created_at: '2026-05-20'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-019
  accepted_decisions: []
implementation_targets:
- local_cli
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-005 - Proposal Decision Shortcut Commands

## Summary

Implement dedicated proposal decision shortcut commands that call the existing decision recording mechanism.

## Rationale

Choice and intake workflows now produce recommended actions that require clear proposal lifecycle commands.

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
