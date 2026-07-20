# Agent Token Budget and Context Discipline

## Provenance

- Proposal: PROP-055
- Source: .p2p/proposals/PROP-055-agent-token-budget-and-context-discipline

## Problem

P2P Engine reduces conversational memory by storing governance state in .p2p and Git, but agents can still consume excessive tokens by scanning broad project context, reading full registries, loading many proposal/change files, or explaining artifacts from conversation memory instead of compact deterministic views. This is especially visible in the P2P Engine repository because the project is using P2P to build P2P, but the risk applies to any large P2P workspace used by CLI or MCP agents.

## Proposal

Introduce an Agent Token Budget and Context Discipline with a narrow MVP based on compact deterministic context packets. The first implementation combines skill policy, CLI context view, and MCP context tool. Agents must read compact summaries first, then details only by explicit ID, and stop once the next bounded action is clear. Add p2p context, p2p context --budget small, p2p context --target ID, and an equivalent p2p_context MCP tool. The context output should include current state, next actions, relevant artifacts, allowed commands, explicit do-not-read guidance, and the smallest sufficient next step. Full repository scans, broad .p2p traversal, full registry reads, source-code exploration, and Git history reads are disallowed unless the user task explicitly requires them or the compact context is insufficient. Advanced token estimation, numeric budgets, read tracking, and model-specific optimization are deferred until after the MVP works in practice.

## Decision

# Decision - PROP-055

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted as the C-light MVP: combine skill policy, CLI compact context, and MCP compact context to reduce agent token consumption without adding advanced token estimation yet.

## Date

2026-05-28

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-722e8d72ceb428111005e047

## Decision Fingerprint

3fb8726465550f533b2c9c5ec24cae9742ab9994f665fd2e01c1a39892576684

## Lineage

None.

## Canonical Source

decision-events.yml
