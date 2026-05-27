# MCP Level 4B Choice Conflict Impact Advisory Tools

## Provenance

- Proposal: PROP-050
- Source: .p2p/proposals/PROP-050-mcp-level-4b-choice-conflict-impact-advisory-tools

## Problem

MCP can create and refine draft proposals, but agents still cannot use existing advisory analysis commands for choice discovery, conflict inspection, or impact prompt generation through MCP.

## Proposal

Add MCP tools p2p_choice_discover, p2p_conflict_status, and p2p_impact_prompt. choice_discover returns advisory findings only. conflict_status reads recorded conflicts only. impact_prompt generates an impact analysis prompt for an existing proposal. Do not add conflict record, choice decide, choice block/unblock, impact import, intake apply, or change/work state transitions.

## Decision

# Decision - PROP-050

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted as MCP Level 4B: expose advisory analysis for choices, conflicts, and impact without governance mutations.

## Date

2026-05-27

## Approver

local
