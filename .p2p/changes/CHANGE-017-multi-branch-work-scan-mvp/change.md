---
change_id: CHANGE-017
title: Multi-Branch Work Scan MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-031
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

# CHANGE-017 - Multi-Branch Work Scan MVP

## Summary

Add p2p work scan to read local branches matching p2p/work/* through Git plumbing, discover .p2p/work/WORK-XXX/manifest.yml files on those branches, and write an aggregated .p2p/registries/work.yml. The command must be read-only with respect to Git: no checkout, fetch, branch creation, commit, PR, or merge.

## Rationale

CHANGE-016 introduced P2P Work manifests and the incremental path toward invisible managed Git. The next step is read-only branch visibility.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Read-only Git adapter functions for local `p2p/work/*` branch discovery.
- `p2p work scan`
- Aggregated `.p2p/registries/work.yml`
- `p2p work list` visibility for scanned branch Work items.
- Tests proving Work manifests can be read from a local P2P-managed branch without checkout.
- P2P skill guidance for branch scan boundaries.

## Acceptance Criteria

- `p2p work scan` reads local branches matching `p2p/work/*`.
- `p2p work scan` discovers `.p2p/work/WORK-XXX/manifest.yml` files on matching branches.
- `p2p work scan` writes `.p2p/registries/work.yml`.
- `p2p work scan` does not checkout, fetch, create branches, commit, submit, or merge.
- `p2p work list` includes scanned branch Work items after scan.
- The command handles repositories with no matching branches gracefully.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.
