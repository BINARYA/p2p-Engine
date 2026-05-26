# Operational Brief

## Where We Are

P2P Engine now has an end-to-end local specification pipeline and the first two levels of invisible managed Git. It can create local Work manifests and scan local `p2p/work/*` branches for Work manifests without checkout.

The project memory is current: registries are not stale, there are 31 proposals and 17 Change Sets, and all recorded Change Sets are completed. `WORK-001` exists as a planned handoff from `CHANGE-012` to the `speckit` export bundle. The work branch scan registry exists, currently with no branch-sourced Work items in this repository.

## Accepted Direction

- P2P remains CLI-first and file-based.
- Change Sets are the operational unit for implementation/export.
- P2P Work is the user-facing abstraction over future managed Git operations.
- Current managed Git levels implemented:
  - Level 1: handoff plan / Work manifest
  - Branch visibility: read-only local `p2p/work/*` scan
- Branches, commits, reviews, and merges remain disabled until explicit future Change Sets implement them.
- Git remains under the hood; normal users interact with Work items, not branch commands.

## Active Work

- `WORK-001` is planned for `CHANGE-012` / `speckit`.
- No Change Set is currently planned or in progress.
- `PROP-002`, `PROP-006`, `PROP-007`, and `PROP-008` remain draft proposals.
- `PROP-003` is deferred.
- `INTAKE-001` is analyzed and has an apply plan.
- `INTAKE-002` is pending.

## Blockers / Inconsistencies

- There are no active formal choice blockers.
- `CHOICE-PROP-008` remains proposal-local vote metadata rather than a project choice.
- P2P can scan local P2P-managed work branches, but cannot yet create managed branches from Work manifests.

## Recommended Next Actions

1. Implement managed branch creation.
   Reason: Work manifests and read-only branch scan now exist; the next incremental step is creating an internal branch from a Work manifest with safety checks.
   Command: `.venv/bin/p2p proposal create "Managed Work Branch Creation MVP"`

2. Review `WORK-001`.
   Reason: `WORK-001` is the first planned handoff manifest and is the natural candidate for branch creation.
   Command: `.venv/bin/p2p work show WORK-001`

3. Review the controlled apply plan for `INTAKE-001`.
   Reason: `INTAKE-001` has a generated apply plan with pending actions.
   Command: `.venv/bin/p2p intake apply show INTAKE-001`

## Not Yet

- Do not commit, submit, review, or merge through P2P yet.
- Do not expose Git as the normal user workflow.
- Do not fetch remote branches during Work scan.
- Do not invoke Spec Kit automatically from the P2P CLI before branch/commit policy is implemented.
