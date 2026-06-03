---
change_id: CHANGE-057
title: MCP End-To-End Proposal Collaboration Workflow
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-075
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

# CHANGE-057 - MCP End-To-End Proposal Collaboration Workflow

## Summary

Define an MCP end-to-end proposal collaboration workflow: create or update draft proposal, persist/commit draft state through an explicit P2P primitive or documented auto-commit policy, create a managed proposal branch from an explicit base branch such as main, request or reference owner consent, publish the branch, and request review. Add MCP tools or behavior such as p2p_project_remote_configure, p2p_consent_request, p2p_proposal_draft_commit, and p2p_proposal_branch with base_branch. Keep p2p_consent_grant owner-controlled; MCP may request consent, but granting consent should remain CLI/UI/server owner action until strong authentication exists.

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
