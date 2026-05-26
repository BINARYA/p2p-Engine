# PROP-014 - Change Set Metadata MVP

## Status

`accepted`

## Problem

P2P Engine has accepted the Change Set and managed Git model, but the CLI cannot yet create or inspect .p2p/changes metadata.

## Context

PROP-013 defines Change Set as the visible operational unit and keeps Git operations metadata-only for the MVP.

## Goals

- Implement p2p change create --from PROP-XXX for accepted proposals.
- Generate .p2p/changes/CHANGE-XXX directories with change.md and metadata files.
- Implement p2p change status and p2p change policy.
- Reject Change Set creation from non-accepted proposals.

## Non-Goals

- Create Git commits, branches, merges, or tags.
- Implement OpenSpec or Spec Kit export.

## Proposal

Add deterministic Change Set metadata generation from accepted proposals and decisions, preserving managed Git as metadata-only.

## Acceptance Criteria

- p2p change create creates a valid CHANGE-XXX folder from an accepted proposal.
- p2p change create rejects draft proposals.
- p2p change status lists Change Sets and lifecycle state.
- p2p change policy shows metadata-only Git policy and reasoning.

## Decision

Pending.
