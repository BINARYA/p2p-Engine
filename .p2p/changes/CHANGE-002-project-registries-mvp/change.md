---
change_id: CHANGE-002
title: Project Registries MVP
status: completed
created_at: '2026-05-20'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-016
  accepted_decisions: []
implementation_targets:
- local_cli
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-002 - Project Registries MVP

## Summary

Add .p2p/registries as a generated index layer for proposals, decisions, changes, choices and relations.

## Rationale

PROP-010 introduced .p2p/project, PROP-012 introduced conflict memory, and PROP-014/015 introduced Change Sets. The next step is making global navigation and provenance explicit.

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
