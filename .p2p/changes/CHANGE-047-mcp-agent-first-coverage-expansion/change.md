---
change_id: CHANGE-047
title: MCP Agent-First Coverage Expansion
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-065
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

# CHANGE-047 - MCP Agent-First Coverage Expansion

## Summary

Expand the P2P MCP tool surface with all priority 1, 2, and 3 agent-safe tools. Keep descriptions explicit about read-only, write-safe, advisory, and governance boundaries. Update tests and agent-facing documentation/skill instructions accordingly.

## Rationale

The owner requested adding MCP coverage for priority 1 read-only tools, priority 2 write-safe deterministic tools, and priority 3 prompt/advisory tools while preserving governance boundaries.

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
