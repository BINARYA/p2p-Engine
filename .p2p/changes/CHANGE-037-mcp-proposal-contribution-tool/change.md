---
change_id: CHANGE-037
title: MCP Proposal Contribution Tool
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-052
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

# CHANGE-037 - MCP Proposal Contribution Tool

## Summary

Add MCP tool p2p_proposal_contribution_add. It appends a typed contribution to a proposal using the existing core contribution model. It may record suggestion, objective, constraint, risk, objection, alternative proposal, and similar contribution types. It must not accept/reject/defer proposals, merge proposals, decide choices, or alter decision files.

## Rationale

The La scatola perfetta test produced multiple related draft proposals. P2P already has a controlled CLI contribution command and core method. Exposing that primitive through MCP is safer than letting agents create separate proposals for every related idea.

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
