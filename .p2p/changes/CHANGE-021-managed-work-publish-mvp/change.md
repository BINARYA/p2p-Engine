---
change_id: CHANGE-021
title: Managed Work Publish MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-035
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

# CHANGE-021 - Managed Work Publish MVP

## Summary

Add p2p work publish WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status review_requested, requires a clean worktree, requires an origin remote, updates the Work manifest to published with remote branch metadata, creates a local publish metadata commit, pushes the managed branch to origin, and leaves PR and merge disabled.

## Rationale

Level 4.5 should be the remote handoff step between local review and owner-controlled merge. It must keep PR creation and merge separate.

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
