---
change_id: CHANGE-030
title: Agent-Safe Project Bootstrap MVP
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-045
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

# CHANGE-030 - Agent-Safe Project Bootstrap MVP

## Summary

Extend p2p init with an optional agent profile and repository mode. Generate generic AGENTS.md plus .p2p/agent-policy.yml. Add p2p agent instructions refresh so Codex, Claude, generic, or all profiles can be added later without replacing previous profiles. Instructions must state that .p2p is managed by P2P commands, missing primitives require stop-and-report, MCP is read-only unless tools explicitly say otherwise, and owner-controlled decisions cannot be made by agents.

## Rationale

The first local MCP test succeeded for read-only status, but an agent then created proposal files and an accepted decision directly under .p2p because the test project lacked P2P agent instructions and MCP write tools.

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
