---
change_id: CHANGE-035
title: MCP Level 4B Choice Conflict Impact Advisory Tools
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-050
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

# CHANGE-035 - MCP Level 4B Choice Conflict Impact Advisory Tools

## Summary

Add MCP tools p2p_choice_discover, p2p_conflict_status, and p2p_impact_prompt. choice_discover returns advisory findings only. conflict_status reads recorded conflicts only. impact_prompt generates an impact analysis prompt for an existing proposal. Do not add conflict record, choice decide, choice block/unblock, impact import, intake apply, or change/work state transitions.

## Rationale

Level 4A completed proposal refinement while keeping governance decisions out of MCP. The next advisory level should expose analysis-only tools that help agents understand divergence and impact without recording decisions or conflicts.

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
