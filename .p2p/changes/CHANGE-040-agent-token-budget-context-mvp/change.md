---
change_id: CHANGE-040
title: Agent Token Budget Context MVP
status: completed
created_at: '2026-05-28'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-055
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

# CHANGE-040 - Agent Token Budget Context MVP

## Summary

Introduce an Agent Token Budget and Context Discipline with a narrow MVP based on compact deterministic context packets. The first implementation combines skill policy, CLI context view, and MCP context tool. Agents must read compact summaries first, then details only by explicit ID, and stop once the next bounded action is clear. Add p2p context, p2p context --budget small, p2p context --target ID, and an equivalent p2p_context MCP tool. The context output should include current state, next actions, relevant artifacts, allowed commands, explicit do-not-read guidance, and the smallest sufficient next step. Full repository scans, broad .p2p traversal, full registry reads, source-code exploration, and Git history reads are disallowed unless the user task explicitly requires them or the compact context is insufficient. Advanced token estimation, numeric budgets, read tracking, and model-specific optimization are deferred until after the MVP works in practice.

## Rationale

The product direction is: AI is expensive, CLI is cheap, Git is memory, .p2p is governance, owner decides, and agents work in bounded sessions. Current skills already require using CLI/MCP primitives and avoiding manual .p2p edits, but they do not yet define an explicit token budget discipline or compact context contract for agents.

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
