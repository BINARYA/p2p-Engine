# PROP-092 - Local MCP Work Lifecycle Parity And Remote Gateway Boundary

## Status

`accepted`

## Problem

P2P Engine can execute the managed Work lifecycle through the CLI, and it already exposes permission-gated MCP tools for several proposal-branch and sync operations. Work items, however, still have only partial MCP coverage: agents can inspect or create Work plans, but cannot use the local MCP adapter to publish, request review, accept, finalize, or clean up Work items through the same domain-specific controls available in the CLI. This leaves agent-first local workflows incomplete and tempts agents or external integrations to fall back to raw Git operations, which would bypass the P2P Work lifecycle, consent receipts, state checks, and audit semantics.

## Context

NEXT-004 identifies Work MCP parity as the next product decision. The accepted permission-gated MCP model in PROP-066 established role plus consent receipts for privileged operations, while the current Work lifecycle already defines branch, submit, review, publish, request-review, accept, finalize, and cleanup transitions in the CLI. The intended boundary is local-first: P2P Engine should provide a complete local MCP/stdIO adapter aligned with the CLI and backed by the same core command layer. Remote multi-user MCP access, authentication, OAuth, client registration, rate limits, billing, tenant isolation, and Wavekit-specific collaboration policy are separate gateway concerns and should not be implemented inside the P2P core. They remain architectural context: Wavekit should be able to reuse the same core commands later, but apply authenticated user grants and stronger server-side receipts outside the local core.

## Goals

- Expose the full managed Work lifecycle through the local P2P MCP adapter with functional parity to the CLI where the corresponding CLI transition already exists.
- Keep every mutating Work MCP operation domain-specific, permission-gated, state-gated, consent-gated, and auditable.
- Reuse the existing Work lifecycle services and P2P command layer instead of duplicating Work logic in CLI, MCP, or future Wavekit adapters.
- Define a stable architectural boundary: P2P core is MCP-ready and local-MCP capable; remote multi-user MCP belongs to a separate Wavekit gateway/control-plane layer.
- Prevent raw Git bypasses by exposing Work operations as P2P tools rather than generic Git tools.

## Non-Goals

- Do not implement a remote HTTP MCP server, OAuth flow, client registration, multi-tenancy, billing, global rate limiting, or hosted project access in P2P Engine core.
- Do not create provider PR/MR automation; provider-specific PR/MR creation remains a separate adapter decision.
- Do not grant agents autonomous authority over owner-controlled actions; owner-controlled transitions still require explicit consent and valid policy checks.
- Do not expose generic Git tools such as arbitrary push, merge, reset, clean, or delete-branch operations.

## Proposal

Introduce local MCP Work lifecycle parity for P2P Engine. The local MCP adapter distributed with P2P Engine should expose the managed Work lifecycle through domain-specific tools that map to the same core services used by the CLI. The intended tool set includes read/status tools that already exist and new mutating tools for Work branch, submit, review, publish, request-review, accept, finalize, and cleanup where the CLI transition exists. Privileged or externally visible transitions must require a valid consent receipt matching operation, target Work ID, actor, and relevant execution context. Tools must fail closed when the Work state, current branch, base branch, worktree cleanliness, remote profile, receipt status, or expected execution context is invalid. Accept must preserve merge-conflict behavior and return structured conflict output instead of pretending that a merge succeeded. Finalize and cleanup must remain separate owner-controlled steps. Cleanup must distinguish local branch deletion from remote branch deletion. All mutating tools must return structured governance/effect metadata and record consent consumption/audit consistently with the proposal-branch MCP pattern. The local MCP adapter may assume a self-managed local trust boundary, but it must not bypass P2P policy or raw Git protections. The remote Wavekit MCP gateway is intentionally out of scope: it should later call the same command layer while adding authenticated principals, client identity, grants, scoped receipts, rate limits, audit retention, and commercial collaboration controls outside the P2P core.

## Acceptance Criteria

- Local MCP exposes Work lifecycle tools for branch, submit, review, publish, request-review, accept, finalize, and cleanup, in addition to existing list/status/show/plan coverage.
- Each mutating Work MCP tool delegates to existing Work lifecycle services or a shared command layer; Work lifecycle rules are not reimplemented separately per adapter.
- Privileged Work MCP operations require consent receipts for the matching operation, target Work ID, and actor_id, and consume or mark receipts with structured result metadata.
- Tools fail closed on invalid Work state, dirty worktree, wrong branch, missing remote, malformed manifest, receipt mismatch, expired receipt, or unauthorized owner-controlled operation.
- Work accept over MCP preserves existing merge-conflict semantics and returns structured conflict data with no finalize or cleanup side effects.
- Work finalize and cleanup remain separate explicit operations; cleanup distinguishes local deletion from optional remote deletion.
- The MCP catalog documents that these are local/core MCP tools, not a remote multi-user Wavekit gateway, and documents Wavekit remote MCP as an out-of-core adapter boundary.
- No generic raw Git MCP tools are introduced for arbitrary push, merge, reset, clean, force-push, or branch deletion.

## Decision

Pending.
