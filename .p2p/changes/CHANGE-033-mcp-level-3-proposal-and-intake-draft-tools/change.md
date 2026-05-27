---
change_id: CHANGE-033
title: MCP Level 3 Proposal and Intake Draft Tools
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-048
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

# CHANGE-033 - MCP Level 3 Proposal and Intake Draft Tools

## Summary

Add MCP tools p2p_proposal_create, p2p_intake_prompt, and p2p_intake_status. These tools may create draft proposals and intake prompts using existing core methods, and may list intake records. They must not accept, reject, defer, decide choices, apply intake recommendations, or manage work merges.

## Rationale

The tested Codex/Codium workflow now correctly stops instead of editing .p2p by hand. The next safe MCP increment should expose draft creation primitives while keeping proposal acceptance and governance decisions owner-controlled.

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
