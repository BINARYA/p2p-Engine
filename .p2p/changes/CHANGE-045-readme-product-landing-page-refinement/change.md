---
change_id: CHANGE-045
title: README Product Landing Page Refinement
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-062
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

# CHANGE-045 - README Product Landing Page Refinement

## Summary

Rewrite README.md with sections: pitch, why, what it does, who it is for, status, 5-minute demo, install, core concepts, docs, roadmap, development. Use HTTPS clone first and keep future hosted product scope out of the engine README.

## Rationale

The repository is being made public. README should explain P2P Engine as the engine, not future hosted products, and route detailed material to docs.

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
