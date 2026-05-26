---
change_id: CHANGE-026
title: Managed Work Cleanup MVP
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-040
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

# CHANGE-026 - Managed Work Cleanup MVP

## Summary

Add p2p work cleanup WORK-XXX. The command requires Work status finalized, a clean worktree, and the current branch to be the Work base branch. It deletes the local managed Work branch by default, can delete the remote Work branch with an explicit --remote flag, records cleanup metadata in the Work manifest, creates a local cleanup metadata commit, and optionally pushes the base branch so cleanup state is persisted remotely.

## Rationale

The managed Work lifecycle now reaches finalization. Cleanup should be separate from finalize so branch deletion remains explicit and reversible by policy.

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
