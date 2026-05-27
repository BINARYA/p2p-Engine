# PROP-050 - MCP Level 4B Choice Conflict Impact Advisory Tools

## Status

`accepted`

## Problem

MCP can create and refine draft proposals, but agents still cannot use existing advisory analysis commands for choice discovery, conflict inspection, or impact prompt generation through MCP.

## Context

Level 4A completed proposal refinement while keeping governance decisions out of MCP. The next advisory level should expose analysis-only tools that help agents understand divergence and impact without recording decisions or conflicts.

## Goals

- Expose choice, conflict, and impact advisory workflows through MCP without adding decision-making mutations.

## Non-Goals

- Pending.

## Proposal

Add MCP tools p2p_choice_discover, p2p_conflict_status, and p2p_impact_prompt. choice_discover returns advisory findings only. conflict_status reads recorded conflicts only. impact_prompt generates an impact analysis prompt for an existing proposal. Do not add conflict record, choice decide, choice block/unblock, impact import, intake apply, or change/work state transitions.

## Acceptance Criteria

- MCP exposes choice discovery, conflict status, and impact prompt tools; tests verify choice discovery is read/advisory, conflict status does not record conflicts, impact prompt writes only prompt artifacts, and governance tools remain absent.

## Decision

Pending.
