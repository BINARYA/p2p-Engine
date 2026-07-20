# MCP Write-Safe Bootstrap Tools MVP

## Provenance

- Proposal: PROP-046
- Source: .p2p/proposals/PROP-046-mcp-write-safe-bootstrap-tools-mvp

## Problem

The MCP server can read project state but cannot perform safe bootstrap operations. When an agent is asked to initialize or harden a project through MCP, it may fall back to manual filesystem edits if no explicit MCP primitive exists.

## Proposal

Add p2p_init_project, p2p_agent_instructions_refresh, and p2p_registry_refresh MCP tools. Keep owner-controlled actions such as proposal accept/reject/defer, choice decide, work accept/finalize/cleanup, and direct Git merge out of MCP. Tool descriptions must make the governance boundary explicit.

## Decision

# Decision - PROP-046

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted as the next controlled MCP increment after agent-safe init: expose only bootstrap and registry refresh primitives, not governance decisions.

## Date

2026-05-27

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-f22a6b8b182d10102e47dedb

## Decision Fingerprint

e5ee08429444255c9f5761d92611779daef8644dffb0e3c368cc440498a92c61

## Lineage

None.

## Canonical Source

decision-events.yml
