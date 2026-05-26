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
