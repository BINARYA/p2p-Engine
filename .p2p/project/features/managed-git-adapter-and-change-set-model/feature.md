# Managed Git Adapter and Change Set Model

## Provenance

- Proposal: PROP-013
- Source: .p2p/proposals/PROP-013-change-set-and-git-branch-model

## Problem

P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## Proposal

Adopt a managed Git model: proposals and change sets are the public P2P concepts, while Git branches, commits, merges, and tags are internal operations selected by a configurable policy. Git details are visible only in verbose/debug modes.

## Decision

# Decision - PROP-013

## Status

`accepted`

## Outcome

accepted

## Decision

Adopt Alternative D - Managed Git Under The Hood.

## Reason

P2P Engine should expose proposal, choice, decision, change, and task concepts to users. Git remains the internal layer for persistence, audit, synchronization, and collaboration, but users should not need to reason about branches, commits, merges, or tags during normal workflows.

## MVP Policy

```yaml
git_policy:
  mode: managed
  operation_level: metadata_only
  expose_git_details: false
  commits:
    auto_commit: false
  branches:
    auto_create: false
  tags:
    auto_create: false
```

## Change Set Policy

- Change Sets can be created only from accepted proposals or accepted decisions.
- Draft proposals can be referenced as non-binding context.
- Change Sets are multi-domain.
- `.p2p/project/features/` is a derived project view.
- Future internal branches require `implementation_ready`, accepted source, plan, tasks, doctor OK, safe worktree or snapshot, recovery strategy, and explicit command or enabled policy.
