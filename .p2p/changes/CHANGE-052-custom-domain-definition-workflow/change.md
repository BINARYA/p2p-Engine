---
change_id: CHANGE-052
title: Custom Domain Definition Workflow
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-071
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

# CHANGE-052 - Custom Domain Definition Workflow

## Summary

Refactor domain initialization around optional templates. Every project has explicit domain state and rubric state. At init, the user may choose no template, a predefined template such as generic/software/grant_document/board_game, or a custom unresolved path. Applying a template pre-populates domain metadata and rubric criteria. Choosing custom or none leaves domain/rubric setup unresolved and creates or recommends first activities for defining the domain and defining the rubric with the user and agent. Maturity assessment becomes assessable only when an enabled rubric exists; unresolved or empty rubrics report a missing/unresolved rubric state instead of well_defined.

## Rationale

Domain and rubric setup should be modeled consistently for every project. Predefined domains should be optional templates that pre-populate domain/rubric metadata, not proof that the project is already semantically well-defined. Custom or no-template projects should start with explicit unresolved domain/rubric state and recommended setup activities.

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
