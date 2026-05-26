---
change_id: CHANGE-025
title: Managed Work Finalize MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-039
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

# CHANGE-025 - Managed Work Finalize MVP

## Summary

Add p2p work finalize WORK-XXX. The command requires Work status accepted, the current branch to match the Work base branch, a clean worktree, and a configured remote. It updates the Work manifest to finalized, records remote/base metadata, creates a local finalize metadata commit, pushes the base branch to the remote, and leaves branch cleanup disabled.

## Rationale

Managed Work now supports plan, branch, submit, review, publish, accept, status, and merge conflict guidance. Finalize should be the explicit post-accept publication step, separate from cleanup and PR creation.

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
