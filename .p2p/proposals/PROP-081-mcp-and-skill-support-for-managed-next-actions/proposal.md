# PROP-081 - MCP and Skill Support for Managed Next Actions

## Status

`accepted`

## Problem

The CLI now supports managed next-action lifecycle commands, but the agent skill and MCP surface still describe p2p_next as read-only/advisory only. Agents using MCP cannot add, complete, retire, or refresh curated next actions, and agents following the skill may not know the CLI lifecycle exists.

## Context

Pending.

## Goals

- Expose the managed next-action lifecycle consistently through CLI guidance, agent skill instructions, and MCP write-safe tools.

## Non-Goals

- Pending.

## Proposal

Add MCP tools p2p_next_add, p2p_next_complete, p2p_next_retire, and p2p_next_refresh. Treat these as write-safe project planning tools without consent receipts because they update the operational next-action board and audit completed/retired entries, but do not decide proposals, merge branches, publish remotes, or change governance policy. Update the p2p-engine skill and MCP documentation to explain that p2p_next remains read/list, while the new tools manage curated next actions. Keep owner-controlled governance boundaries intact.

## Acceptance Criteria

- MCP tool definitions include p2p_next_add, p2p_next_complete, p2p_next_retire, and p2p_next_refresh; tool handlers call the same workspace methods as the CLI; tests cover add, complete, retire, refresh, and log creation through MCP; docs/MCP and the p2p-engine skill describe the lifecycle; p2p validate and the test suite pass.

## Decision

Pending.
