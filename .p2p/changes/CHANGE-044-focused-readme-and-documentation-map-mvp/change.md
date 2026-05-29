---
change_id: CHANGE-044
title: Focused README and Documentation Map MVP
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-061
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

# CHANGE-044 - Focused README and Documentation Map MVP

## Summary

Refine documentation with four steps: rewrite README.md around what P2P Engine is, what it does, repository components, installation, quick start, and agent usage; keep docs/INSTALL.md; add docs/CLI-GUIDE.md, docs/MCP.md, docs/AGENT-INTEGRATION.md, and docs/API.md as structured stubs; and create a documentation index in README.md describing each docs file.

## Rationale

P2P Engine documentation now has an installation guide, but the repository still needs a focused README and stubs for the detailed documentation areas identified as important for humans, agents, and contributors.

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
