---
change_id: CHANGE-041
title: Project Definition Maturity Rubrics MVP
status: completed
created_at: '2026-05-28'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-056
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

# CHANGE-041 - Project Definition Maturity Rubrics MVP

## Summary

Add Project Definition Maturity Rubrics. A project may define a domain and an enabled list of criteria under .p2p/project/rubrics.yml. The first MVP ships deterministic built-in rubrics for at least generic and software domains, with an architecture that can add grant_document, board_game, hardware, service, and other domains later. The init flow should be able to create an initial rubric profile, and a dedicated command should refresh/show maturity assessment. The assessment should scan P2P project artifacts conservatively and report each criterion as covered, partial, or missing, with evidence IDs when available. Scores represent definition maturity: whether the planned project has treated relevant topics enough for export, not whether implementation has been completed.

## Rationale

P2P Engine aims to export a project definition toward downstream generators, agents, OpenSpec/Spec Kit, or implementation workflows. Different project domains require different definition criteria: software, grant/bid documents, board games, documents, hardware, services, and other domains need different rubrics. The init wizard can ask for a project domain and create a rubric checklist that becomes the deterministic driver for future maturity assessment.

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
