---
change_id: CHANGE-039
title: Project Readiness Assessment MVP
status: completed
created_at: '2026-05-28'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-054
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

# CHANGE-039 - Project Readiness Assessment MVP

## Summary

Adopt a hybrid assessment model. Level 1 computes a deterministic completion/readiness score from P2P state: validation results, stale registries, draft proposals, accepted proposals, open choices, blockers, change/work lifecycle status and operational brief availability. Level 2 adds domain maturity rubrics through explicit criteria files and prompt/import workflows. Software rubrics may cover architecture, security, usability, testability, maintainability, packaging and documentation. Generic or non-software rubrics can be added per supported project type. Assessment output must include score, confidence, factors, gaps and suggested next actions.

## Rationale

Recent MCP tests show that agents can now create and refine draft proposals safely. The next product layer should help owners and agents reason about project readiness without pretending that subjective quality is fully objective. Different project domains need different maturity criteria, such as software security/usability/maintainability or non-software domain-specific criteria.

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
