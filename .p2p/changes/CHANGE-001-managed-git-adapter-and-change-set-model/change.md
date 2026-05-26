---
change_id: CHANGE-001
title: Managed Git Adapter and Change Set Model
status: completed
created_at: '2026-05-20'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-013
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

# CHANGE-001 - Managed Git Adapter and Change Set Model

## Summary

Adopt a managed Git model: proposals and change sets are the public P2P concepts, while Git branches, commits, merges, and tags are internal operations selected by a configurable policy. Git details are visible only in verbose/debug modes.

## Rationale

The current foundation still risks coupling proposals and branches too tightly. PROP-012 introduced impact/conflict memory; the next step is a managed Git adapter model with explicit change sets and a user-facing workflow based on P2P concepts rather than Git concepts.

## Scope

### Included

- Define Change Set as the visible operational unit after accepted proposal or decision.
- Keep Git as an internal adapter with metadata-only behavior in the MVP.
- Define the execution/export target taxonomy:
  - `execution_domains` describes the type of work.
  - `implementation_targets` describes where the work is implemented.
  - `spec_targets` describes normalized P2P specification outputs.
  - `export_targets` describes downstream export formats/tools.
- Preserve OpenSpec and Spec Kit as downstream export targets, not the source of truth.

### Excluded

- Automatic Git commits, branches, tags, or merges.
- Direct export from raw proposal folders to OpenSpec or Spec Kit.
- Adopting OpenSpec or Spec Kit as the internal P2P model.

## Deliverables

- Managed Git domain model.
- Metadata-only Git policy.
- Change Set artifact structure.
- Target taxonomy for execution, implementation, spec, and export.
- CLI design boundary for future Git diagnostics and export workflows.

## Acceptance Criteria

- Change Set metadata separates `execution_domains`, `implementation_targets`, `spec_targets`, and `export_targets`.
- `p2p change show` surfaces the target taxonomy.
- Registries preserve target taxonomy for Change Sets.
- Git policy remains metadata-only for the MVP.
- OpenSpec and Spec Kit are represented as downstream export targets.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
