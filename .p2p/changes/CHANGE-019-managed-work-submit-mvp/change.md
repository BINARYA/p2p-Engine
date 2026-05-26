---
change_id: CHANGE-019
title: Managed Work Submit MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-033
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

# CHANGE-019 - Managed Work Submit MVP

## Summary

Add p2p work submit WORK-XXX. The command verifies the current branch is the Work branch, validates that the Work item is branched, requires changed files, records the changed file list, updates the Work manifest to submitted, stages the Work branch changes, and creates a local commit with a P2P-standard message.

## Rationale

The managed Git path should keep Git under the hood while giving the owner a clear Work lifecycle before later review and merge steps.

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
