---
change_id: CHANGE-027
title: Remote Project Profile and Review Request Policy
status: completed
created_at: '2026-05-27'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-041
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

# CHANGE-027 - Remote Project Profile and Review Request Policy

## Summary

Add a Remote Project Profile and a provider-agnostic review-request command. The profile records mode, provider, remote name, and remote URL. p2p work request-review WORK-XXX records that a published Work item is ready for external review, emits provider-specific guidance, and leaves merge/accept owner-controlled.

## Rationale

The owner wants GitHub/GitLab support to remain optional and adapter-based while keeping Git invisible under P2P Work commands.

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
