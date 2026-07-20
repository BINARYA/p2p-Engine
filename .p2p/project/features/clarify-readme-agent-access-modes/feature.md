# Clarify README Agent Access Modes

## Provenance

- Proposal: PROP-070
- Source: .p2p/proposals/PROP-070-clarify-readme-agent-access-modes

## Problem

The README says to connect an agent through MCP but does not clearly distinguish CLI access from MCP access. This can make MCP appear complete even though the current MCP surface is intentionally agent-safe and excludes privileged governance, imports, Git operations, and Work lifecycle actions.

## Proposal

Update README's 5-minute agent setup to describe two valid agent connection modes: CLI access and MCP access. Add a short warning that MCP is currently an agent-safe tool surface and not the full P2P command surface.

## Decision

# Decision - PROP-070

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to clarify README quick start semantics: agents can use CLI or MCP, and MCP is intentionally limited until permission/ownership governance is decided.

## Date

2026-05-29

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-b67e941a7f11fb901bb90d11

## Decision Fingerprint

f8541318d3f9114ad43adda15d9123dd43aa643ec44988b8f27909d764e3d76f

## Lineage

None.

## Canonical Source

decision-events.yml
