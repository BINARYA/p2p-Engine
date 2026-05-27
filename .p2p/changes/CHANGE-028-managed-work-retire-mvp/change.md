---
change_id: CHANGE-028
title: Managed Work Retire MVP
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-043
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

# CHANGE-028 - Managed Work Retire MVP

## Summary

Add p2p work retire WORK-XXX --reason TEXT. The command requires Work status planned, updates the manifest status to retired, records retirement metadata, and makes p2p work status report no next action for retired Work.

## Rationale

WORK-001 is a planned speckit handoff for CHANGE-012, but CHANGE-012 and the speckit exporter are already completed. P2P needs a first-class way to retire obsolete planned Work items instead of editing manifests by hand.

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
