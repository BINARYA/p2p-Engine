# PROP-031 - Multi-Branch Work Scan MVP

## Status

`accepted`

## Problem

P2P Work manifests can represent handoff plans locally, but P2P still cannot discover Work manifests that live on parallel P2P-managed branches without checking them out.

## Context

CHANGE-016 introduced P2P Work manifests and the incremental path toward invisible managed Git. The next step is read-only branch visibility.

## Goals

- Let P2P scan local P2P-managed Git branches for Work manifests without checkout or mutation.

## Non-Goals

- Pending.

## Proposal

Add p2p work scan to read local branches matching p2p/work/* through Git plumbing, discover .p2p/work/WORK-XXX/manifest.yml files on those branches, and write an aggregated .p2p/registries/work.yml. The command must be read-only with respect to Git: no checkout, fetch, branch creation, commit, PR, or merge.

## Acceptance Criteria

- p2p work scan lists local Work manifests and writes .p2p/registries/work.yml. p2p work list can include local manifests and scanned branch manifests. The scan handles non-Git or no-branch repositories gracefully. Tests cover scanning a P2P-managed branch without checkout.

## Decision

Pending.
