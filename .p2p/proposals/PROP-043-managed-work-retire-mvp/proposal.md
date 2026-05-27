# PROP-043 - Managed Work Retire MVP

## Status

`accepted`

## Problem

Obsolete planned Work manifests can remain in project status even after their source Change Set or export has already been completed, causing stale next actions.

## Context

WORK-001 is a planned speckit handoff for CHANGE-012, but CHANGE-012 and the speckit exporter are already completed. P2P needs a first-class way to retire obsolete planned Work items instead of editing manifests by hand.

## Goals

- Add an explicit p2p work retire command for obsolete planned Work manifests.
- Record retired status, reason, and date in the Work manifest.
- Keep retirement metadata-only and avoid Git branch, commit, push, merge, or cleanup side effects.

## Non-Goals

- Retire branched, submitted, published, accepted, finalized, or cleaned Work items in this MVP.
- Delete Work manifests or generated exports.

## Proposal

Add p2p work retire WORK-XXX --reason TEXT. The command requires Work status planned, updates the manifest status to retired, records retirement metadata, and makes p2p work status report no next action for retired Work.

## Acceptance Criteria

- p2p work retire WORK-001 --reason TEXT marks a planned Work manifest retired.
- p2p work status shows retired Work with next none.
- The command refuses non-planned Work statuses.
- Tests cover successful retire and invalid status refusal.

## Decision

Pending.
