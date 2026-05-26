---
change_id: CHANGE-022
title: Managed Work Accept MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-036
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

# CHANGE-022 - Managed Work Accept MVP

## Summary

Add p2p work accept WORK-XXX. The command requires Work status published, a clean Git worktree, the Work branch to exist locally, and the current branch to be the manifest base branch. It performs a local no-ff merge from the managed branch, records accepted/merged metadata in the Work manifest, commits that metadata on the base branch, and leaves push and cleanup disabled.

## Rationale

Level 5 should integrate published Work only through an explicit owner action, while keeping push to the base branch and branch cleanup separate.

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
