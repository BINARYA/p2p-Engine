---
change_id: CHANGE-024
title: Managed Work Merge Conflict Guidance MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-038
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

# CHANGE-024 - Managed Work Merge Conflict Guidance MVP

## Summary

Enhance p2p work accept with conflict guidance. On merge conflict, mark the Work manifest as merge_conflict, record source/base branches and conflicted files, and show recovery commands. Add p2p work accept --continue WORK-XXX to finalize after manual conflict resolution, and p2p work accept --abort WORK-XXX to abort the merge and restore the Work item to published.

## Rationale

Managed Work Level 5 exists. Before adding finalize, cleanup, or GitHub PR flow, accept must leave the repository and Work manifest in a clear state when a merge conflict occurs.

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
