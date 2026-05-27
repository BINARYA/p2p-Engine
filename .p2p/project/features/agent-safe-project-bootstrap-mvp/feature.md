# Agent-Safe Project Bootstrap MVP

## Provenance

- Proposal: PROP-045
- Source: .p2p/proposals/PROP-045-agent-safe-project-bootstrap-mvp

## Problem

New P2P projects do not give Codex, Claude, or other agents explicit boundaries. Agents can infer .p2p internals, edit files directly, invent IDs, or make owner-controlled decisions when an MCP or CLI primitive is missing.

## Proposal

Extend p2p init with an optional agent profile and repository mode. Generate generic AGENTS.md plus .p2p/agent-policy.yml. Add p2p agent instructions refresh so Codex, Claude, generic, or all profiles can be added later without replacing previous profiles. Instructions must state that .p2p is managed by P2P commands, missing primitives require stop-and-report, MCP is read-only unless tools explicitly say otherwise, and owner-controlled decisions cannot be made by agents.

## Decision

# Decision - PROP-045

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted as the immediate hardening step after the MCP local test showed that agents need explicit project-level boundaries before write-capable MCP tools are added.

## Date

2026-05-27

## Approver

local
