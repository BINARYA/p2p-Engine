# Managed Work Status Summary MVP

## Provenance

- Proposal: PROP-037
- Source: .p2p/proposals/PROP-037-managed-work-status-summary-mvp

## Problem

The managed Work lifecycle now spans plan, branch, submit, review, publish, and accept, but users lack a single read-only view that explains each Work item state and next action.

## Proposal

Add p2p work status. The command reads local Work manifests and scanned branch registry entries, summarizes each Work item, and derives a conservative next command from status without modifying project or Git state.

## Decision

# Decision - PROP-037

## Status

`accepted`

## Outcome

accepted

## Reason

This is the safest next refinement: a read-only operational view before conflict handling, finalize, or GitHub PR work.

## Date

2026-05-26

## Approver

local
