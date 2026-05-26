# PROP-012 - Impact Map and Conflict Memory

## Status

`accepted`

## Problem

P2P Engine can generate a rationalized project state, but it does not yet capture what a proposal touches or whether it overlaps, depends on, supersedes, or conflicts with other proposals.

## Context

PROP-010 and PROP-011 introduced .p2p/project as project state. The next step is preserving impact and conflict memory so accepted decisions are not reconsidered accidentally.

## Goals

- Define proposal-level impact-map artifacts.
- Define conflict memory in .p2p/project/conflicts.yml.
- Add prompt-only analysis for impact, overlap, dependencies, and conflicts.
- Add CLI commands to record and inspect conflicts.

## Non-Goals

- Automatically reject proposals without human decision.
- Implement full AI agent invocation.

## Proposal

Add impact and conflict artifacts that allow P2P Engine to understand which project areas a proposal touches and preserve memory of competing or mutually exclusive alternatives.

## Acceptance Criteria

- A proposal can generate an impact prompt.
- Impact artifacts can be imported into a proposal folder.
- Conflicts can be recorded in .p2p/project/conflicts.yml and inspected from the CLI.

## Decision

Pending.
