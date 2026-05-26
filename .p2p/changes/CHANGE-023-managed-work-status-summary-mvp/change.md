---
change_id: CHANGE-023
title: Managed Work Status Summary MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-037
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

# CHANGE-023 - Managed Work Status Summary MVP

## Summary

Add p2p work status. The command reads local Work manifests and scanned branch registry entries, summarizes each Work item, and derives a conservative next command from status without modifying project or Git state.

## Rationale

After Level 5, the base workflow exists but needs a safer operational summary before adding GitHub PR or finalize behavior.

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
