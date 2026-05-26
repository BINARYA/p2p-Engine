# PROP-015 - Change Set Lifecycle and Task Tracking

## Status

`accepted`

## Problem

P2P Engine can create metadata-only Change Sets, but it cannot yet move them through an operational lifecycle or inspect their tasks/actions.

## Context

PROP-014 introduced .p2p/changes metadata. The next step is making Change Sets usable for following execution progress.

## Goals

- Implement Change Set lifecycle transitions from proposed to completed.
- Validate allowed status transitions.
- Show tasks and actions for a Change Set.
- Keep the MVP metadata-only without Git writes.

## Non-Goals

- Implement automatic task execution.
- Create Git branches or commits.

## Proposal

Add lifecycle commands and task/action inspection for Change Sets so P2P can track operational progress.

## Acceptance Criteria

- A Change Set can transition through planned, implementation_ready, in_progress, in_review and completed.
- Invalid transitions are rejected with a clear error.
- p2p change show displays a Change Set summary.
- p2p change tasks displays tasks and actions from the Change Set artifacts.

## Decision

Pending.
