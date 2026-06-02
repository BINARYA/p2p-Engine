# Concurrent Managed Work and Merge Decision Model

## Provenance

- Proposal: PROP-072
- Source: .p2p/proposals/PROP-072-concurrent-managed-work-and-merge-decision-model

## Problem

P2P Engine needs a first-class collaboration model for multiple people and agents working through Git without needing to understand Git. Main must represent accepted project state, but new proposal drafts, proposal refinements, and implementation candidates may be produced concurrently by different contributors. Today the managed Work lifecycle covers implementation branches, but proposal-level collaboration, candidate selection, and merge decisions across concurrent contributors are not specified as a single CLI-facing workflow.

Without this model, users may treat main as a shared scratchpad for draft proposals, agents may not know when to branch or publish, and P2P lacks a first-class way to compare, select, reject, combine, or merge competing proposal/work candidates before they alter accepted project state.

## Proposal

Introduce a Concurrent Managed Collaboration model with P2P-owned CLI operations for proposal branches, Work branches, remote synchronization, candidate decisions, and owner-controlled merges.

Core rule: `main` contains accepted project state only. Draft proposals, proposal refinements, alternative proposal candidates, and implementation Work candidates must live on P2P-managed branches until explicitly accepted and merged by an authorized owner or governance process.

Branch classes:

- `p2p/proposal/<proposal-id>-<slug>-<actor-slug>-<hash16>`: a managed branch for creating or refining proposal state.
- `p2p/work/<work-id>-<change-id>-<target>`: the existing managed branch class for implementation work.

Resolved design choices:

- Draft proposal work stays off `main` by default.
- Proposal branches use real `PROP-XXX` identifiers, not temporary candidate IDs.
- Proposal branch names include a stable 16-hex-character hash suffix for branch-name disambiguation.
- P2P must mitigate concurrent proposal ID collisions by fetching/scanning accepted and remote proposal state before allocating IDs, then validating again before publish/merge.
- P2P must expose user-facing remote operations through CLI commands, because users and routine agents should not need to understand fetch, pull, push, or PR/MR mechanics.
- Work selection is required only when multiple Work candidates exist for one Change Set.
- Combining candidates creates a new auditable Work item or proposal branch derived from the selected source candidates.

Proposal ID allocation and collision rule:

For cloud-backed projects, `p2p proposal create` and `p2p proposal branch` must perform a remote-aware allocation pass when a remote profile is configured:

```text
1. fetch configured remote metadata;
2. scan local main, local P2P proposal branches, remote main, and remote P2P proposal branches;
3. allocate the next available PROP-XXX ID;
4. create a branch name with capped slug, actor slug, and hash-16 suffix;
5. record actor, allocation, hash, and remote scan metadata in the proposal branch;
6. re-check for ID collision before publish and before merge.
```

Concurrent ID allocation is treated as a recoverable publish-time conflict, not as silent corruption. If publish detects that the remote already contains a conflicting `PROP-XXX` proposal branch or accepted proposal, P2P must stop, fetch, allocate the next available proposal ID, and either ask for confirmation or proceed only when an explicit `--auto-renumber` option or policy allows it. Safe auto-renumber must rewrite the local proposal directory, proposal metadata, title references where applicable, branch metadata, and branch name from the losing ID to the new ID before retrying publication. The old local branch must be retired or deleted only after the new proposal branch is safely created and validated.

This fetch/scan/recheck/renumber strategy is sufficient for the MVP but is not a perfect distributed lock. A later enhancement may add a remote lock ref or allocation manifest if strict sequential IDs are required under simultaneous branch creation. Hashing the user or agent into the branch name reduces branch-name collisions, but it does not replace the human-readable `PROP-XXX` ID.

Proposal branch lifecycle:

```text
planned -> branched -> revised -> review_requested -> published -> accepted -> merged -> finalized
                                   -> rejected -> retired
                                   -> merge_conflict -> accepted|aborted
```

Work candidate lifecycle extends the existing Work lifecycle with candidate decision states:

```text
planned -> branched -> submitted -> review_requested -> published -> review_handoff
                                                        -> selected -> accepted -> finalized -> cleaned_up
                                                        -> rejected|retired
                                                        -> merge_conflict -> accepted|aborted
```

Minimum proposal CLI operations:

```bash
p2p proposal branch PROP-XXX
p2p proposal status PROP-XXX
p2p proposal publish PROP-XXX
p2p proposal publish PROP-XXX --auto-renumber
p2p proposal request-review PROP-XXX
p2p proposal accept-branch PROP-XXX --reason "..."
p2p proposal reject-branch PROP-XXX --reason "..."
p2p proposal merge PROP-XXX
p2p proposal merge --continue PROP-XXX
p2p proposal merge --abort PROP-XXX
p2p proposal retire-branch PROP-XXX --reason "..."
p2p proposal scan
```

Minimum P2P-managed remote/sync operations:

```bash
p2p sync fetch
p2p sync status
p2p sync pull
p2p sync push
p2p proposal publish PROP-XXX
p2p work publish WORK-XXX
p2p work request-review WORK-XXX
p2p work finalize WORK-XXX
```

These commands wrap Git transport operations and enforce P2P validation, branch policy, remote profile checks, actor attribution, and audit recording. They should never require Matteo, Lorenzo, or routine agents to run raw Git commands.

Minimum candidate CLI operations for concurrent Work:

```bash
p2p work plan CHANGE-XXX --author "matteo" --agent "codex"
p2p work list --change CHANGE-XXX
p2p work compare WORK-001 WORK-002
p2p work select WORK-001 --reason "..."
p2p work reject WORK-002 --reason "..."
p2p work combine WORK-001 WORK-003 --reason "..."
```

Existing implementation commands remain the execution path after candidate selection:

```bash
p2p work branch WORK-XXX
p2p work submit WORK-XXX
p2p work review WORK-XXX
p2p work publish WORK-XXX
p2p work request-review WORK-XXX
p2p work accept WORK-XXX
p2p work accept --continue WORK-XXX
p2p work accept --abort WORK-XXX
p2p work finalize WORK-XXX
p2p work cleanup WORK-XXX
p2p work retire WORK-XXX
```

Local/cloud semantics:

```text
local: branch local, review local, merge local, audit local.
cloud: fetch remote state, branch local, publish branch to remote, optional PR/MR handoff, merge/finalize against remote-backed base branch, audit local plus remote metadata.
```

Remote-backed projects must not change the core lifecycle. They add remote profile validation, safe fetch/pull/push wrappers, branch publication, provider-specific review automation or guidance, and final base-branch push.

Candidate decision model:

- Independent proposal branches may be accepted and merged separately if validation passes and no project-state conflict is detected.
- Competing proposal branches for the same problem should create or reference a P2P Choice before one is accepted.
- Multiple Work candidates may exist for one Change Set.
- A Work candidate must be selected before owner-controlled accept/merge when more than one candidate exists for the same Change Set.
- Rejected and retired candidates remain auditable and must not disappear from project history.
- Combining candidates should create a new Work item or proposal branch that records its source candidates rather than silently mutating one branch.

Required engine hardening:

- Validation must report duplicate proposal IDs as an explicit P2P error.
- Registry generation must fail clearly or mark an error when duplicate proposal IDs exist; it must not silently produce ambiguous project state.
- Proposal lookup must preserve the current ambiguity guard and user-facing commands must surface actionable recovery guidance.
- Publish and merge operations must re-run duplicate-ID checks against local and fetched remote state.
- Auto-renumber must be safe, auditable, and non-destructive until the replacement branch is created and validated.

Audit metadata required for proposal and Work branch decisions:

```text
actor_id
actor_type: person|agent
agent_profile, when applicable
source_branch
base_branch
proposal_id, when applicable
change_id, when applicable
work_id, when applicable
branch_hash16
decision_kind: accept|reject|select|combine|retire|merge|abort|finalize
id_allocation_source
id_collision_check
remote_scan_commit
review_status
local_commit
merge_commit
remote_name
remote_url
remote_branch
review_url, when available
conflict_files
created_at
decided_at
```

Agent instruction requirements:

- Generated `AGENTS.md`, Codex skill instructions, and Claude/generic agent instructions must state that agents use P2P CLI commands for managed proposal, Work, and sync operations.
- Agents must not run raw `git branch`, `git merge`, `git fetch`, `git pull`, `git push`, or provider-specific PR commands for managed project state unless a user explicitly authorizes an escape hatch.
- Agents must inspect P2P status and sync status before creating proposal or Work branches.
- Agents must keep draft proposal work off `main` unless the project policy explicitly allows direct-owner drafts on main.
- Agents must stop and ask for owner approval before accept, merge, finalize, cleanup, or remote publication if policy marks those actions as owner-controlled.

This proposal intentionally defines the CLI-facing collaboration model. Permission-gated MCP exposure of these operations remains part of PROP-066.

## Decision

# Decision - PROP-072

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted as the core CLI-facing collaboration model for concurrent proposal branches, managed remote sync, candidate Work selection, safe proposal ID collision handling, and agent-safe Git abstraction.

## Date

2026-06-02

## Approver

davide
