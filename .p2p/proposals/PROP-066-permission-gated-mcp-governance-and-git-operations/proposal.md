# PROP-066 - Permission-Gated MCP Governance And Git Operations

## Status

`draft`

## Problem

The MCP surface intentionally excludes governance, ownership-sensitive, import, Git lifecycle, and repository publishing operations. These capabilities may become useful for advanced agent workflows, but exposing them before a repository permission and ownership model is defined would let agents perform actions that should remain owner-controlled.

## Context

Current MCP tools are limited to read-only, write-safe deterministic, and advisory prompt operations. Deferred operations include proposal accept/reject/defer, choice decide/block, conflict/vote/precedent record, spec import, Work branch/submit/review/publish/accept/finalize/cleanup, and commit/push/merge/PR workflows.

## Goals

- Preserve the future requirement so the missing MCP operations are not forgotten.
- Make implementation explicitly dependent on a decided repository permission and ownership structure.
- Define the operations as privileged MCP capabilities rather than normal agent-safe primitives.

## Non-Goals

- Implement these privileged MCP methods now.
- Allow agents to bypass owner governance decisions.
- Expose Git commit, push, merge, or PR creation without an accepted permission model.

## Proposal

Add a future MCP capability set for owner-authorized governance and repository operations, but keep it deferred until P2P has an accepted permission and ownership model for repositories. The future design must specify who owns the repository, who can authorize governance actions, which MCP clients or agents can request privileged operations, how consent is represented, how actions are audited, and which operations require interactive confirmation or explicit owner approval.

## Acceptance Criteria

- The proposal lists the deferred MCP operations: proposal accept/reject/defer; choice decide/block; conflict, vote, and precedent record; spec import; Work branch/submit/review/publish/accept/finalize/cleanup; commit, push, merge, and PR workflows.
- The proposal states that implementation is blocked until repository permissions and ownership are decided.
- The proposal distinguishes privileged MCP operations from the current read-only, write-safe, and advisory MCP surface.
- No privileged MCP operation is implemented as part of this proposal.

## Decision

Pending.
