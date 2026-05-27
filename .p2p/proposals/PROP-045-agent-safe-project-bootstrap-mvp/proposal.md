# PROP-045 - Agent-Safe Project Bootstrap MVP

## Status

`accepted`

## Problem

New P2P projects do not give Codex, Claude, or other agents explicit boundaries. Agents can infer .p2p internals, edit files directly, invent IDs, or make owner-controlled decisions when an MCP or CLI primitive is missing.

## Context

The first local MCP test succeeded for read-only status, but an agent then created proposal files and an accepted decision directly under .p2p because the test project lacked P2P agent instructions and MCP write tools.

## Goals

- Generate agent-safe project instructions during init and provide a repeatable command to add or refresh instructions for additional agent profiles later.

## Non-Goals

- Pending.

## Proposal

Extend p2p init with an optional agent profile and repository mode. Generate generic AGENTS.md plus .p2p/agent-policy.yml. Add p2p agent instructions refresh so Codex, Claude, generic, or all profiles can be added later without replacing previous profiles. Instructions must state that .p2p is managed by P2P commands, missing primitives require stop-and-report, MCP is read-only unless tools explicitly say otherwise, and owner-controlled decisions cannot be made by agents.

## Acceptance Criteria

- p2p init creates AGENTS.md and .p2p/agent-policy.yml by default; an initial agent profile can be selected without becoming permanent; p2p agent instructions refresh can add Codex, Claude, generic, or all instruction files; tests verify missing primitive behavior and owner-controlled boundaries are present.

## Decision

Pending.
