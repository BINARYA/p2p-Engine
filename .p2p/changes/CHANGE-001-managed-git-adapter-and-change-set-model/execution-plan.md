# Execution Plan - PROP-013

## Objective

Define the managed Git model that separates user-facing P2P concepts from internal Git operations and introduces change sets as the operational implementation unit.

## Workstreams

### WS1 - Domain Model

Define Proposal, Choice, Decision, Change Set, Git Adapter, Branch, Commit, Merge, and Tag.

### WS2 - Managed Git Policy

Define `git_policy.yml`, including branch, commit, merge, tag, and debug visibility rules.

### WS3 - Change Set Structure

Define `.p2p/changes/CHANGE-XXX/` artifacts.

The MVP Change Set must be created only from accepted proposals or accepted decisions. Draft proposals can be references but not binding scope.

`change.md` uses YAML frontmatter for machine-readable metadata and Markdown sections for human-readable scope, rationale, deliverables, acceptance criteria, dependencies, risks, and related choices.

Change Set lifecycle:

```text
proposed → planned → implementation_ready → in_progress → in_review → completed
```

Side states:

```text
blocked
cancelled
superseded
```

### WS4 - CLI Design

Specify future commands without implementing risky Git operations yet.

## MVP Recommendation

Start with change-set metadata and managed Git policy. Delay real Git branch/commit/merge automation until policy, doctor checks, and verbose/debug output are stable.

Change Sets must support non-software domains. Software-specific exports such as OpenSpec or Spec Kit are downstream targets, not the definition of a Change Set.
