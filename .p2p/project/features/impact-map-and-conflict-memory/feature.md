# Impact Map and Conflict Memory

## Provenance

- Proposal: PROP-012
- Source: .p2p/proposals/PROP-012-impact-map-and-conflict-memory

## Problem

P2P Engine can generate a rationalized project state, but it does not yet capture what a proposal touches or whether it overlaps, depends on, supersedes, or conflicts with other proposals.

## Proposal

Add impact and conflict artifacts that allow P2P Engine to understand which project areas a proposal touches and preserve memory of competing or mutually exclusive alternatives.

## Decision

# Decision - PROP-012

## Status

`accepted`

## Outcome

accepted

## Reason

Impact analysis and conflict memory are implemented as prompt-only impact artifacts plus persistent .p2p/project/conflicts.yml commands.

## Date

2026-05-20

## Approver

local
