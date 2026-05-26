# PROP-037 - Managed Work Status Summary MVP

## Status

`accepted`

## Problem

The managed Work lifecycle now spans plan, branch, submit, review, publish, and accept, but users lack a single read-only view that explains each Work item state and next action.

## Context

After Level 5, the base workflow exists but needs a safer operational summary before adding GitHub PR or finalize behavior.

## Goals

- Provide a readable p2p work status summary that reports Work state, branch, target, remote/acceptance metadata, and the next suggested command.

## Non-Goals

- Pending.

## Proposal

Add p2p work status. The command reads local Work manifests and scanned branch registry entries, summarizes each Work item, and derives a conservative next command from status without modifying project or Git state.

## Acceptance Criteria

- p2p work status lists Work items with status, change, target, branch and next action; it handles planned, branched, submitted, review_requested, published, accepted, and scanned Work items; tests cover summary output; the P2P skill documents using status before lifecycle commands.

## Decision

Pending.
