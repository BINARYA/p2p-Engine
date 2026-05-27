---
change_id: CHANGE-034
title: MCP Level 4A Proposal Refinement Tools
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-049
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

# CHANGE-034 - MCP Level 4A Proposal Refinement Tools

## Summary

Add MCP tools p2p_proposal_update, p2p_project_brief_prompt, and p2p_project_brief_show. Proposal update may replace structured proposal sections. Project brief prompt may create prompt/context artifacts, and brief show may read an imported brief. No brief import, proposal decision, choice decision, or work lifecycle mutation is added in this level.

## Rationale

Level 3 intentionally stopped before governance decisions. The next advisory workflow increment should support draft refinement and operational synthesis prompts without accepting proposals or applying decisions.

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
