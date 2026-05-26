# Exploration - PROP-013

## Interpretation

PROP-013 clarifies the relationship between P2P concepts and Git. The key correction is:

```text
Proposal != Branch
```

A proposal is a decision artifact. A change set is the operational package that turns accepted decisions into implementation work. Branches, commits, merges, and tags are internal Git operations managed by P2P Engine through policy.

The user should not need to think in Git terms.

```text
User sees:
  proposal → choice → decision → change → task

P2P manages internally:
  files → commit → branch → merge → tag
```

## Proposed Lifecycle

```text
idea / contribution
→ proposal
→ exploration
→ impact/conflict analysis
→ choices
→ decision
→ change set
→ internal Git operations, when policy requires them
→ .p2p/project refresh
```

## Definitions

```text
Proposal
  Decision unit stored under .p2p/proposals/.

Choice
  Open alternative that requires a decision.

Decision
  Recorded governance outcome.

Change Set
  Operational package that groups accepted proposals, decisions, plan, tasks,
  files, and internal Git metadata.

Git Adapter
  Internal P2P component that translates P2P operations into branch, commit,
  merge, tag, archive, and sync operations.

Branch
  Internal Git workspace used when policy requires isolation, review,
  collaboration, or implementation separation.

Commit
  Internal audit checkpoint created by P2P policy.

Merge
  Git event that makes the change set part of the official project state.

Tag
  Optional internal reference for decisions, changes, and releases.
```

## Branch Decision Risk

The main risk is arbitrary branch selection. If the user must decide case by case, the workflow becomes inconsistent and too technical.

The mitigation is to move the decision into managed Git policy:

```text
git_policy.yml
  mode: managed
  expose_git_details: false
  proposal_branching: auto
  change_branching: auto
  commits: auto
  tags: decision/change tags when useful
```

The CLI can explain the policy decision in verbose/debug mode, but the default UX remains P2P-native.

## Initial Rule

Git is managed under the hood.

```text
proposal
  public decision artifact

change set
  public operational artifact

branch/commit/merge/tag
  internal Git adapter details
```

## Suggested Commands

```bash
p2p change create --from PROP-013
p2p change status CHANGE-001
p2p change policy CHANGE-001
p2p change close CHANGE-001 --merged

p2p status --verbose
p2p doctor
```
