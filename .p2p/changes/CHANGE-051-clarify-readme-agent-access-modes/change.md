---
change_id: CHANGE-051
title: Clarify README Agent Access Modes
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-070
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

# CHANGE-051 - Clarify README Agent Access Modes

## Summary

Update README's 5-minute agent setup to describe two valid agent connection modes: CLI access and MCP access. Add a short warning that MCP is currently an agent-safe tool surface and not the full P2P command surface.

## Rationale

P2P Engine supports agent-mediated use through CLI access or MCP access. CLI access can reach the full local command surface when the owner explicitly authorizes actions. MCP access is structured and safer, but intentionally limited until a repository permission and ownership model is accepted.

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
