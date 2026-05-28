---
change_id: CHANGE-042
title: Guided Rubric Selection MVP
status: completed
created_at: '2026-05-28'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-057
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

# CHANGE-042 - Guided Rubric Selection MVP

## Summary

Add Guided Rubric Selection During Init. When p2p init runs interactively, after project domain selection it should ask whether to customize rubric criteria. If the owner says no, P2P keeps all domain criteria enabled. If the owner says yes, P2P asks an enable/disable confirmation for each suggested criterion and saves the selected enabled flags into .p2p/project/rubrics.yml. Scripted init with a project name remains non-interactive and uses the full default rubric for the selected domain.

## Rationale

Project definition maturity is now based on .p2p/project/rubrics.yml. The rubric file already supports enabled/disabled criteria, and the assessment ignores disabled criteria. Therefore the init wizard can offer a lightweight owner confirmation step without adding custom criteria, keyword editing, or advanced UI.

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
