---
change_id: CHANGE-048
title: Agent-First Setup Documentation Split
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-067
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

# CHANGE-048 - Agent-First Setup Documentation Split

## Summary

Revise README and INSTALL around an agent-first new-project setup model. Add or update agent setup guidance so the P2P Engine checkout, target project, and agent client are clearly separated. Move repository-contributor instructions for installing P2P and enabling an agent against the P2P Engine repository into CONTRIBUTING.md, and keep README limited to a concise contribution pointer.

## Rationale

README currently has a 5-minute demo with manual CLI commands. INSTALL documents source installation, project init, MCP setup, and manual first commands. CONTRIBUTING has basic developer setup but does not clearly explain how contributors should enable their agent to add proposals to the P2P Engine project state.

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
