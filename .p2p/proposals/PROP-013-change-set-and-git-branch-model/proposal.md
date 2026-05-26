# PROP-013 - Managed Git Adapter and Change Set Model

## Status

`accepted`

## Problem

P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## Context

The current foundation still risks coupling proposals and branches too tightly. PROP-012 introduced impact/conflict memory; the next step is a managed Git adapter model with explicit change sets and a user-facing workflow based on P2P concepts rather than Git concepts.

## Goals

- Define Change Set as the operational unit after proposal decision.
- Define Git as an internal adapter for persistence, audit, collaboration, and synchronization.
- Hide branch, commit, merge, and tag details from the default user experience.
- Reduce discretion in branch decisions through configurable Git policy.
- Preserve proposal and decision history in .p2p artifacts even when Git branches are removed.

## Non-Goals

- Implement full Git branch automation in this proposal.
- Require users to understand or manually manage Git branches.
- Let AI agents bypass P2P CLI by manipulating Git directly.

## Proposal

Adopt a managed Git model: proposals and change sets are the public P2P concepts, while Git branches, commits, merges, and tags are internal operations selected by a configurable policy. Git details are visible only in verbose/debug modes.

## Acceptance Criteria

- The proposal defines Proposal, Choice, Decision, Change Set, Git Adapter, Branch, Commit, Merge, and Tag.
- The proposal defines a managed Git policy for branch/commit/tag behavior.
- The proposal defines an initial .p2p/changes structure.
- The proposal addresses the risk of arbitrary branch decisions by moving the choice into explicit policy.

## Decision

Accepted. P2P Engine adopts Managed Git Under The Hood with Change Set as the visible operational unit. The MVP remains metadata-only for Git operations.
