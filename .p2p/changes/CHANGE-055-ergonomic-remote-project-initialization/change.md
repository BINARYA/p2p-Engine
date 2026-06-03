---
change_id: CHANGE-055
title: Ergonomic Remote Project Initialization
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-073
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

# CHANGE-055 - Ergonomic Remote Project Initialization

## Summary

Extend p2p init and remote profile setup with an ergonomic remote initialization flow. Add init options such as --repository cloud, --provider, --remote, and --remote-url. During init, P2P should write the project remote profile, detect whether the named Git remote exists, compare its URL when present, and print actionable follow-up commands when Git state is missing or mismatched. The command should not create provider resources in the MVP. Existing p2p project remote configure remains available for later edits, and p2p sync status remains the validation command after setup.

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
