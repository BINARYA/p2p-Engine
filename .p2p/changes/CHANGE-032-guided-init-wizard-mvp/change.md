---
change_id: CHANGE-032
title: Guided Init Wizard MVP
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-047
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

# CHANGE-032 - Guided Init Wizard MVP

## Summary

When p2p init is called without a project name, run a small interactive wizard that asks project name, initial agent profile, repository mode, and whether to show an MCP setup hint. Keep p2p init NAME --agent ... --repository ... as the scriptable path. Print concrete next steps after initialization.

## Rationale

After the MCP local test, the product direction is to make project bootstrap safe and understandable before expanding MCP mutations. The CLI should guide first-time users while keeping scriptable flags available.

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
