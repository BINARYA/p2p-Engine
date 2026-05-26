---
change_id: CHANGE-011
title: Controlled Intake Apply Workflow
status: completed
created_at: '2026-05-25'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-025
  accepted_decisions: []
implementation_targets:
- local_cli
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-011 - Controlled Intake Apply Workflow

## Summary

Implement a two-phase controlled intake apply workflow. The plan command converts suggested-actions.yml into a versioned apply-plan.yml with support classifications. The show command displays the plan. The run command applies one explicit supported action and writes applied-actions.yml, while governance-only actions remain preview-only.

## Rationale

The project now supports operational briefs, p2p next, and choice discovery/blocking. Intake apply should follow the same source-of-truth discipline: plan first, show reviewable actions, run only explicit supported actions, and log what was applied.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Controlled intake apply plan/show/run commands.
- Versioned `apply-plan.yml` artifacts for intake records.
- Versioned `applied-actions.yml` audit log for successful runs.
- MVP support for explicit `add_contribution` and `open_choice` applications.
- Updated P2P skill guidance.

## Acceptance Criteria

- `p2p intake apply plan INTAKE-XXX` writes `apply-plan.yml`.
- `p2p intake apply show INTAKE-XXX` displays planned actions.
- `p2p intake apply run` supports `add_contribution`.
- `p2p intake apply run` supports `open_choice` only with at least two `--option` values.
- Governance-only actions are preview-only and cannot be applied by intake apply.
- `applied-actions.yml` records every successful application.
- Tests cover the plan/show/run workflow.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
