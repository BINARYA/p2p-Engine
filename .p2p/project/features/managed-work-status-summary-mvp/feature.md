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

## Event Type

accepted

## Effective State

accepted

## Reason

This is the safest next refinement: a read-only operational view before conflict handling, finalize, or GitHub PR work.

## Date

2026-05-26

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-3baf130fe918d77863dd2599

## Decision Fingerprint

ab9fc9efab6739c7d93eafde1f044f761f6e766c77b771d526fcb3fccb60abbf

## Lineage

None.

## Canonical Source

decision-events.yml
