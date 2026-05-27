---
change_id: CHANGE-036
title: Draft Proposal Next Action and Agent Explanation Guard
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-051
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

# CHANGE-036 - Draft Proposal Next Action and Agent Explanation Guard

## Summary

Update fallback next actions to recommend reviewing the first draft proposal when no stronger action exists. Update generated AGENTS.md, Codex project skill, Claude instructions, .p2p/agent-policy.yml, and the repository P2P skill so agents must use proposal/choice/change/work show or MCP equivalents before explaining existing artifacts.

## Rationale

The La scatola perfetta MCP test created a correct draft proposal, but next action remained weak. The agent explanation was good, but it should be anchored to current P2P state rather than conversation memory.

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
