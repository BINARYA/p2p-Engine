---
change_id: CHANGE-060
title: Managed Next Action Lifecycle
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-079
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

# CHANGE-060 - Managed Next Action Lifecycle

## Summary

Implement a hybrid next-action lifecycle. Curated active actions remain in .p2p/project/next-actions.yml. Completed and retired curated actions are moved to .p2p/project/next-actions-log.yml with status, reason, and date. Generated actions are computed at runtime from project state using the existing fallback/blocker logic and shown alongside curated actions with clear source labels. Add CLI commands p2p next list, p2p next add, p2p next complete, p2p next retire, and p2p next refresh. The default p2p next view should list curated plus generated actions with deduplication by kind/target. p2p next complete NEXT-003 --reason ... should remove the obsolete curated item from active next actions and record an audit log entry.

## Rationale

Not provided.

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
