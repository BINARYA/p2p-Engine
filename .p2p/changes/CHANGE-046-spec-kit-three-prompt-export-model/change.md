---
change_id: CHANGE-046
title: Spec Kit Three-Prompt Export Model
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-064
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

# CHANGE-046 - Spec Kit Three-Prompt Export Model

## Summary

Implement an agent-first project definition export pipeline. Step 1 synthesizes accepted P2P memory into project.md using a required core checklist, domain extensions, evidence labels, and explicit missing-information markers. Step 2 derives target-specific outputs from project.md: generic exports project.md and propose.md; OpenSpec exports propose.md aligned with OpenSpec proposal principles; Spec Kit exports speckit.constitution.md, speckit.specify.md, and speckit.plan.md aligned with the three starting Spec Kit prompts. Legacy bundle-style exports may remain temporarily under a legacy/ or bundle/ path, but they must be labeled secondary and not documented as the primary flow.

## Rationale

Accepted PROP-027 and PROP-028 implemented conservative file bundle exports from P2P-native software specs. User review showed this does not match the desired integration contract. Spec Kit starts from three agent prompts: constitution, specify, and plan. OpenSpec starts from a proposal-oriented input. Generic export should be a readable full project definition and a project/proposal initialization input. Therefore project.md should become the canonical generic synthesis artifact, and downstream exports should be deterministic views derived from it and its P2P evidence.

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
