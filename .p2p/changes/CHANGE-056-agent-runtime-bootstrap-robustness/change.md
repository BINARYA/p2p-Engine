---
change_id: CHANGE-056
title: Agent Runtime Bootstrap Robustness
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-074
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

# CHANGE-056 - Agent Runtime Bootstrap Robustness

## Summary

Introduce an Agent Runtime Bootstrap Robustness model. Generated AGENTS.md, agent policy, and docs should include a runtime discovery sequence: try p2p, try repository-local virtualenv paths when present, try python -m p2p_engine if the package is importable, then check MCP availability. Add a diagnostic command or script such as p2p doctor, p2p agent doctor, or a lightweight repo-local bootstrap hint that reports whether p2p CLI, MCP server, Git, and project root are usable. For cloud environments, provide a documented install/bootstrap path that agents can request from the owner rather than stopping with only p2p command not found. The Missing Primitive Rule remains valid, but the error should include actionable recovery steps.

## Rationale

Not provided.

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
