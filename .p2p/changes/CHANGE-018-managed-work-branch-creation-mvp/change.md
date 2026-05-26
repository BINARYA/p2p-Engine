---
change_id: CHANGE-018
title: Managed Work Branch Creation MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-032
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

# CHANGE-018 - Managed Work Branch Creation MVP

## Summary

Add p2p work branch WORK-XXX. The command validates a clean Git repository, reads the Work manifest branch name, creates and checks out the managed branch, updates the manifest to branched, and keeps commit/merge actions disabled.

## Rationale

The project policy keeps Git invisible to the user while using managed work branches under the hood to avoid divergence on main.

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
