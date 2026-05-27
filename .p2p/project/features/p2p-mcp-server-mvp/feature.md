# P2P MCP Server MVP

## Provenance

- Proposal: PROP-044
- Source: .p2p/proposals/PROP-044-p2p-mcp-server-mvp

## Problem

Agents should access P2P project state through structured tools instead of parsing CLI text or reading .p2p files directly.

## Proposal

Add src/p2p_engine/mcp with a small JSON-RPC stdio MCP server and a p2p-mcp-server entrypoint. The server exposes read-only tools for project status, next actions, proposal list/show, choice list/show, change status, work status, and registry show. Each tool returns structured JSON derived from P2PWorkspace.

## Decision

# Decision - PROP-044

## Status

`accepted`

## Outcome

accepted

## Reason

A local read-only MCP server is the safest first agent-facing interface over the deterministic P2P Core.

## Date

2026-05-27

## Approver

local
