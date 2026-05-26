# Next Action Recommender MVP

## Provenance

- Proposal: PROP-023
- Source: .p2p/proposals/PROP-023-next-action-recommender-mvp

## Problem

The project now stores operational next-actions, but there is no top-level command that answers what to do next, and project status does not surface the operational brief state.

## Proposal

Implement an advisory next-action recommender. The command should prefer imported next-actions.yml, fall back to deterministic project state checks, support --top N, and project status should summarize whether an operational brief exists plus the first suggested action.

## Decision

# Decision - PROP-023

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to connect operational brief next-actions to a top-level advisory p2p next command and concise project status summary.

## Date

2026-05-25

## Approver

local
