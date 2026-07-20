# P2P Core CLI MCP Mediator Web Boundary

## Provenance

- Proposal: PROP-042
- Source: .p2p/proposals/PROP-042-p2p-core-cli-mcp-mediator-web-boundary

## Problem

P2P Engine needs a clear product and architecture boundary before adding MCP, mediator, web UI, or direct AI integrations. Without this boundary, the deterministic engine risks being coupled to optional AI or web infrastructure too early.

## Proposal

Adopt a five-layer architecture: Level 1 P2P Core, Level 2 P2P CLI, Level 3 Skill/MCP/Agent Interfaces, Level 4 P2P Mediator, Level 5 P2P Web. Core remains deterministic and provider-neutral. Intelligence lives in optional mediator or agent-facing layers. MCP exposes core capabilities to agents and mediators. Governance decisions remain owner-controlled unless an explicit future policy permits bounded automation.

## Decision

# Decision - PROP-042

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

The five-layer boundary keeps the core deterministic and open-source usable while allowing optional MCP, mediator, and web layers to evolve independently.

## Date

2026-05-27

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-92468b24ea8efc1e612b671d

## Decision Fingerprint

72ad8aa0cfe1a6f4dd3a19b65df920f80a11635ffd8f5ca7f04b082ff7de0023

## Lineage

None.

## Canonical Source

decision-events.yml
