# PROP-010 - P2P Project State Model

## Status

`accepted`

## Problem

Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.

## Context

OpenSpec and Spec Kit are useful downstream targets, but P2P Engine needs its own intermediate project model before exporting to those tools.

## Goals

- Define a P2P-native project state generated from accepted proposals.
- Create a dedicated `.p2p/project/` area for rationalized project artifacts.
- Specify how accepted proposals update project state.
- Keep OpenSpec and Spec Kit as downstream exporters, not the source of truth.

## Non-Goals

- Implement a full OpenSpec or Spec Kit exporter in this proposal.
- Replace proposal, decision, plan, or task artifacts.

## Proposal

Add a P2P project state model that turns accepted proposals into versioned project artifacts under `.p2p/project/`. The MVP uses explicit refresh via `p2p project refresh`; automatic refresh after acceptance can be added later.

## Acceptance Criteria

- The proposal defines the `.p2p/project/` directory structure.
- The proposal defines when and how accepted proposals update project state.
- The proposal distinguishes P2P-native project state from OpenSpec and Spec Kit exports.

## Decision

Accepted. P2P Engine should maintain a versioned `.p2p/project/` layer as the rationalized project state derived from accepted proposals and decisions.
