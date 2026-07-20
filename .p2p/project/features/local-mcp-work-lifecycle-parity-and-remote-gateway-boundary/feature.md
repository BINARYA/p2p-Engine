# Local MCP Work Lifecycle Parity And Remote Gateway Boundary

## Provenance

- Proposal: PROP-092
- Source: .p2p/proposals/PROP-092-local-mcp-work-lifecycle-parity-and-remote-gateway-boundary

## Problem

P2P Engine can execute the managed Work lifecycle through the CLI, and it already exposes permission-gated MCP tools for several proposal-branch and sync operations. Work items, however, still have only partial MCP coverage: agents can inspect or create Work plans, but cannot use the local MCP adapter to publish, request review, accept, finalize, or clean up Work items through the same domain-specific controls available in the CLI. This leaves agent-first local workflows incomplete and tempts agents or external integrations to fall back to raw Git operations, which would bypass the P2P Work lifecycle, consent receipts, state checks, and audit semantics.

## Proposal

Introduce local MCP Work lifecycle parity for P2P Engine. The local MCP adapter distributed with P2P Engine should expose the managed Work lifecycle through domain-specific tools that map to the same core services used by the CLI. The intended tool set includes read/status tools that already exist and new mutating tools for Work branch, submit, review, publish, request-review, accept, finalize, and cleanup where the CLI transition exists. Privileged or externally visible transitions must require a valid consent receipt matching operation, target Work ID, actor, and relevant execution context. Tools must fail closed when the Work state, current branch, base branch, worktree cleanliness, remote profile, receipt status, or expected execution context is invalid. Accept must preserve merge-conflict behavior and return structured conflict output instead of pretending that a merge succeeded. Finalize and cleanup must remain separate owner-controlled steps. Cleanup must distinguish local branch deletion from remote branch deletion. All mutating tools must return structured governance/effect metadata and record consent consumption/audit consistently with the proposal-branch MCP pattern. The local MCP adapter may assume a self-managed local trust boundary, but it must not bypass P2P policy or raw Git protections. The remote Wavekit MCP gateway is intentionally out of scope: it should later call the same command layer while adding authenticated principals, client identity, grants, scoped receipts, rate limits, audit retention, and commercial collaboration controls outside the P2P core.

## Decision

# Decision - PROP-092

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner accepted local MCP Work lifecycle parity as the core direction: P2P Engine exposes the full Work lifecycle through local MCP using domain-specific, permission-gated commands, while remote multi-user MCP remains a separate Wavekit gateway boundary.

## Date

2026-07-04

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-43ee93f4bad029501144e656

## Decision Fingerprint

73e6a51ac7b74ca441ae6cadb249f74be04ce2ed3a1b5f515c93c544e46f45b8

## Lineage

None.

## Canonical Source

decision-events.yml
