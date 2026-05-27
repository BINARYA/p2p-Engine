---
change_id: CHANGE-031
title: MCP Write-Safe Bootstrap Tools MVP
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-046
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

# CHANGE-031 - MCP Write-Safe Bootstrap Tools MVP

## Summary

Add p2p_init_project, p2p_agent_instructions_refresh, and p2p_registry_refresh MCP tools. Keep owner-controlled actions such as proposal accept/reject/defer, choice decide, work accept/finalize/cleanup, and direct Git merge out of MCP. Tool descriptions must make the governance boundary explicit.

## Rationale

CHANGE-030 added agent-safe init and instruction refresh in the CLI/Core. The next increment is to expose only those safe bootstrap mutations through MCP, without adding governance decisions or managed-work mutations.

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
