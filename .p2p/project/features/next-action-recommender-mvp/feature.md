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

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to connect operational brief next-actions to a top-level advisory p2p next command and concise project status summary.

## Date

2026-05-25

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-b87673d0dc521e8af87fe8e8

## Decision Fingerprint

5cac653c259b95f63154d93986d7f52c966ba930d0eb24fc262d2bae29ba5cbb

## Lineage

None.

## Canonical Source

decision-events.yml
