---
change_id: CHANGE-029
title: P2P MCP Server MVP
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-044
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

# CHANGE-029 - P2P MCP Server MVP

## Summary

Add src/p2p_engine/mcp with a small JSON-RPC stdio MCP server and a p2p-mcp-server entrypoint. The server exposes read-only tools for project status, next actions, proposal list/show, choice list/show, change status, work status, and registry show. Each tool returns structured JSON derived from P2PWorkspace.

## Rationale

PROP-042 established that MCP is an agent-facing interface over the deterministic P2P Core, not the mediator itself. The first MCP implementation should be local, read-only, and provider-neutral.

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
