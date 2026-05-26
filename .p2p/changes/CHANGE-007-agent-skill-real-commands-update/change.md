---
change_id: CHANGE-007
title: Agent Skill Real Commands Update
status: completed
created_at: '2026-05-20'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-021
  accepted_decisions: []
implementation_targets:
- local_cli
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-007 - Agent Skill Real Commands Update

## Summary

Refresh .codex/skills/p2p-engine/SKILL.md so agents use the current CLI as the source of truth.

## Rationale

P2P Engine now has stable commands for proposal list/show, intake prompt/import/status, choice create/list/decide and proposal accept/reject/defer.

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
