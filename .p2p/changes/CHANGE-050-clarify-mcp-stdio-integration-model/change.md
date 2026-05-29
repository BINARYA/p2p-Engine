---
change_id: CHANGE-050
title: Clarify MCP Stdio Integration Model
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-069
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

# CHANGE-050 - Clarify MCP Stdio Integration Model

## Summary

Update docs/INSTALL.md and docs/MCP.md with a clear MCP stdio model, verified client setup sections, and explicit notes about future Streamable HTTP for shared long-running multi-client services. Keep all examples based on the current Python MCP server command and --root target-project argument.

## Rationale

P2P Engine currently exposes a local stdio MCP server through the Python module p2p_engine.mcp.server. In stdio mode, each MCP client starts its own local process and shared project state lives in the target repository, .p2p, Git, and P2P core storage. The docs should distinguish this from future shared Streamable HTTP operation.

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
