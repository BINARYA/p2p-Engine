---
change_id: CHANGE-062
title: MCP and Skill Support for Managed Next Actions
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-081
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

# CHANGE-062 - MCP and Skill Support for Managed Next Actions

## Summary

Add MCP tools p2p_next_add, p2p_next_complete, p2p_next_retire, and p2p_next_refresh. Treat these as write-safe project planning tools without consent receipts because they update the operational next-action board and audit completed/retired entries, but do not decide proposals, merge branches, publish remotes, or change governance policy. Update the p2p-engine skill and MCP documentation to explain that p2p_next remains read/list, while the new tools manage curated next actions. Keep owner-controlled governance boundaries intact.

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
