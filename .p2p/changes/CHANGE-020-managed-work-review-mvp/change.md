---
change_id: CHANGE-020
title: Managed Work Review MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-034
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

# CHANGE-020 - Managed Work Review MVP

## Summary

Add p2p work review WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status submitted, requires a clean worktree, records the commit to review, updates the Work manifest to review_requested, creates a local metadata commit, and leaves push/PR/merge disabled.

## Rationale

Level 4 should prepare the review handoff while keeping remote push, PR creation, and merge out of scope until later levels.

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
