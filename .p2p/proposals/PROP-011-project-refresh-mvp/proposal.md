# PROP-011 - Project Refresh MVP

## Status

`accepted`

## Problem

P2P Engine has accepted the .p2p/project state model, but the CLI cannot yet generate or inspect that rationalized project layer.

## Context

PROP-010 accepted .p2p/project as the versioned project state derived from accepted proposals.

## Goals

- Implement p2p project refresh to generate the first .p2p/project artifacts.
- Implement p2p project status to inspect generated project state.
- Implement p2p project show to read generated project sections.

## Non-Goals

- Implement OpenSpec or Spec Kit export.
- Implement automatic refresh after decision record.

## Proposal

Add deterministic project-state generation from accepted proposals, starting with overview, problem, scope, project SWOT placeholder, features, decisions-map, and conflicts.

## Acceptance Criteria

- p2p project refresh creates .p2p/project with deterministic files.
- p2p project status reports accepted proposal count and feature count.
- p2p project show can print overview or a feature.

## Decision

Pending.
