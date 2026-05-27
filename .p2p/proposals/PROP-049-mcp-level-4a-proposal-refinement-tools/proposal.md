# PROP-049 - MCP Level 4A Proposal Refinement Tools

## Status

`accepted`

## Problem

MCP can create draft proposals and intake prompts, but agents still cannot refine an existing draft proposal or generate/show the operational project brief through MCP. This limits iterative proposal development after Level 3.

## Context

Level 3 intentionally stopped before governance decisions. The next advisory workflow increment should support draft refinement and operational synthesis prompts without accepting proposals or applying decisions.

## Goals

- Allow MCP clients to update draft proposal content and generate/show project brief artifacts while keeping governance owner-controlled.

## Non-Goals

- Pending.

## Proposal

Add MCP tools p2p_proposal_update, p2p_project_brief_prompt, and p2p_project_brief_show. Proposal update may replace structured proposal sections. Project brief prompt may create prompt/context artifacts, and brief show may read an imported brief. No brief import, proposal decision, choice decision, or work lifecycle mutation is added in this level.

## Acceptance Criteria

- MCP exposes proposal update and project brief prompt/show tools; proposal update modifies proposal sections without changing decision status; project brief prompt returns context and prompt paths; project brief show returns stored brief or a clear error if missing; tests cover the flow and governance tools remain absent.

## Decision

Pending.
