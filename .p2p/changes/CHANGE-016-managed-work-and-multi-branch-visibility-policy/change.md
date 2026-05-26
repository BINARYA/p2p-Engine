---
change_id: CHANGE-016
title: Managed Work and Multi-Branch Visibility Policy
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-030
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

# CHANGE-016 - Managed Work and Multi-Branch Visibility Policy

## Summary

Introduce P2P Work as the user-facing abstraction over future Git branches. Define levels from advisory to handoff plan, managed branch, managed commit, managed review, and owner-controlled merge. Implement p2p work plan/list/show to create and inspect .p2p/work/WORK-XXX/manifest.yml for validated spec exports. This first MVP must not create branches, commits, PRs, or merges.

## Rationale

CHANGE-001 established managed Git as an internal adapter. CHANGE-012 through CHANGE-015 created a spec/export/validate pipeline. The next step is to define work manifests and the incremental path toward invisible managed Git.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Managed Git policy levels from advisory to owner-controlled merge.
- `p2p work plan --change CHANGE-XXX --target TARGET`
- `p2p work list`
- `p2p work show WORK-XXX`
- `.p2p/work/WORK-XXX/manifest.yml` model.
- Work manifest fields for source Change Set, proposals, handoff target, export validation, logical branch name, allowed files, and disabled auto branch/commit/merge policy.
- P2P skill guidance for routing comments, choices, Change Sets, exports, and Work manifests.
- Tests for manifest creation and inspection.

## Acceptance Criteria

- `p2p work plan --change CHANGE-XXX --target TARGET` requires a validated export bundle.
- `p2p work plan` creates `.p2p/work/WORK-XXX/manifest.yml`.
- Work manifests include source Change Set, source proposals, handoff target, export path, export validation status, logical internal branch name, allowed files, and managed Git levels.
- Work policy keeps `auto_branch`, `auto_commit`, and `auto_merge` disabled in this MVP.
- `p2p work list` lists planned Work manifests.
- `p2p work show WORK-XXX` prints manifest detail.
- The MVP does not create Git branches, commits, PRs, tags, or merges.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
