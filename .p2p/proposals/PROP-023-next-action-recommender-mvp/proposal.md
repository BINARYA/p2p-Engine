# PROP-023 - Next Action Recommender MVP

## Status

`accepted`

## Problem

The project now stores operational next-actions, but there is no top-level command that answers what to do next, and project status does not surface the operational brief state.

## Context

The owner decided that p2p next should be top-level, advisory only, list ordered actions with --top support, read .p2p/project/next-actions.yml when present, and compute conservative fallback actions when it is missing or empty.

## Goals

- Add top-level p2p next.
- Read imported next-actions.yml as advisory source.
- Compute conservative fallback actions from stale registries, incomplete Change Sets, pending intake, and open or draft choices.
- Add a concise operational section to p2p project status.

## Non-Goals

- Do not modify project state from p2p next.
- Do not make owner decisions automatically.

## Proposal

Implement an advisory next-action recommender. The command should prefer imported next-actions.yml, fall back to deterministic project state checks, support --top N, and project status should summarize whether an operational brief exists plus the first suggested action.

## Acceptance Criteria

- p2p next lists ordered advisory actions.
- p2p next --top 1 shows only the first action.
- p2p next falls back when next-actions.yml is missing or empty.
- p2p project status shows operational brief availability, next action count, and first next action summary.

## Decision

Pending.
