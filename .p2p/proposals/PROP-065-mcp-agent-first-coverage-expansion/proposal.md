# PROP-065 - MCP Agent-First Coverage Expansion

## Status

`accepted`

## Problem

The CLI contains many read-only, write-safe, and prompt/advisory workflows that are useful for agents, but the MCP server exposes only a limited subset. This makes MCP less effective as the primary agent substrate, especially after agent-first project export became central.

## Context

The owner requested adding MCP coverage for priority 1 read-only tools, priority 2 write-safe deterministic tools, and priority 3 prompt/advisory tools while preserving governance boundaries.

## Goals

- Expose read-only MCP tools for Change Sets, Work, registries, project state, remote profile, and spec/export inspection.
- Expose write-safe deterministic MCP tools for Change Set creation, project refresh, spec refresh/export/validation, and Work planning.
- Expose prompt/advisory MCP tools for explore, digest, clarify, synthesize, plan, tasks, swot, and spec refinement prompts.

## Non-Goals

- Expose owner-governance decisions such as proposal accept/reject/defer, choice decide/block/unblock, conflict record, vote record, or work branch/merge/finalize operations.
- Expose import/apply workflows that ingest external AI output without a separate trust and preview model.

## Proposal

Expand the P2P MCP tool surface with all priority 1, 2, and 3 agent-safe tools. Keep descriptions explicit about read-only, write-safe, advisory, and governance boundaries. Update tests and agent-facing documentation/skill instructions accordingly.

## Acceptance Criteria

- MCP exposes the requested priority 1 read-only tools.
- MCP exposes the requested priority 2 write-safe deterministic tools.
- MCP exposes the requested priority 3 prompt/advisory tools.
- MCP still does not expose owner-controlled governance decisions, direct Git lifecycle operations, or import/apply commands.
- Tests cover tool definitions and representative calls for read-only, write-safe, and prompt/advisory additions.

## Decision

Pending.
