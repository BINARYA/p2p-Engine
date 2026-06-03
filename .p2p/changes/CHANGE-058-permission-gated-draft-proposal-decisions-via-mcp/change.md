---
change_id: CHANGE-058
title: Permission-Gated Draft Proposal Decisions via MCP
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-077
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

# CHANGE-058 - Permission-Gated Draft Proposal Decisions via MCP

## Summary

Add p2p_proposal_accept, p2p_proposal_reject, and p2p_proposal_defer MCP tools. Each tool must require proposal_id, actor_id, consent_id, and reason, validate a granted consent receipt for operation proposal_accept/proposal_reject/proposal_defer targeting the proposal ID and actor, call the same workspace decision path used by the CLI, consume the consent with audit metadata, and document that MCP can request but not grant consent.

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
