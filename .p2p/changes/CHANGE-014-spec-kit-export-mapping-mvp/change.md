---
change_id: CHANGE-014
title: Spec Kit Export Mapping MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-028
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

# CHANGE-014 - Spec Kit Export Mapping MVP

## Summary

Add speckit as a supported p2p spec export target. Export to .p2p/outputs/spec-export/CHANGE-XXX/speckit/specs/CHANGE-XXX-slug/ with spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md, contracts/README.md, and manifest.yml. The mapping should preserve P2P provenance and mark unresolved implementation details as NEEDS CLARIFICATION instead of inventing them.

## Rationale

CHANGE-013 added generic and OpenSpec-oriented software spec exports. Spec Kit expects a specification-driven feature directory with spec, plan, supporting design artifacts and tasks.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- `p2p spec export --change CHANGE-XXX --target speckit`
- Spec Kit-oriented export index and manifest.
- Feature directory under `.p2p/outputs/spec-export/CHANGE-XXX/speckit/specs/CHANGE-XXX-slug/`
- `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, and `contracts/README.md`
- P2P skill guidance for Spec Kit export usage and governance boundary.
- Tests covering successful Spec Kit export and export inspection.

## Acceptance Criteria

- `p2p spec export --change CHANGE-XXX --target speckit` writes a Spec Kit-oriented feature directory.
- The feature directory includes `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, and `contracts/README.md`.
- Exported Spec Kit artifacts preserve P2P provenance and mark unresolved implementation details as `NEEDS CLARIFICATION`.
- `p2p spec export-status` lists the `speckit` target.
- `p2p spec export-show CHANGE-XXX --target speckit` prints the Spec Kit export index.
- Tests cover successful Spec Kit export and inspection.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
