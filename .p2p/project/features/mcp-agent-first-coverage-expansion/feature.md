# MCP Agent-First Coverage Expansion

## Provenance

- Proposal: PROP-065
- Source: .p2p/proposals/PROP-065-mcp-agent-first-coverage-expansion

## Problem

The CLI contains many read-only, write-safe, and prompt/advisory workflows that are useful for agents, but the MCP server exposes only a limited subset. This makes MCP less effective as the primary agent substrate, especially after agent-first project export became central.

## Proposal

Expand the P2P MCP tool surface with all priority 1, 2, and 3 agent-safe tools. Keep descriptions explicit about read-only, write-safe, advisory, and governance boundaries. Update tests and agent-facing documentation/skill instructions accordingly.

## Decision

# Decision - PROP-065

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to expose priority 1 read-only, priority 2 write-safe deterministic, and priority 3 prompt/advisory MCP tools while preserving owner-only governance boundaries.

## Date

2026-05-29

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-f662a92ee466a07eafcb46b8

## Decision Fingerprint

9e654834d6e191b0ab69a97aeae7ec0c3c578ee59001aff13e2d4fceda6fb3f4

## Lineage

None.

## Canonical Source

decision-events.yml
