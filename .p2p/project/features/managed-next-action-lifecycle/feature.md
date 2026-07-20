# Managed Next Action Lifecycle

## Provenance

- Proposal: PROP-079
- Source: .p2p/proposals/PROP-079-managed-next-action-lifecycle

## Problem

P2P next actions can become stale because .p2p/project/next-actions.yml is curated project state but the CLI only reads it. There is no managed command to add, complete, retire, or refresh next actions, so agents either leave obsolete items such as completed consolidation tasks visible or must edit .p2p state by hand, which violates the managed-state boundary.

## Proposal

Implement a hybrid next-action lifecycle. Curated active actions remain in .p2p/project/next-actions.yml. Completed and retired curated actions are moved to .p2p/project/next-actions-log.yml with status, reason, and date. Generated actions are computed at runtime from project state using the existing fallback/blocker logic and shown alongside curated actions with clear source labels. Add CLI commands p2p next list, p2p next add, p2p next complete, p2p next retire, and p2p next refresh. The default p2p next view should list curated plus generated actions with deduplication by kind/target. p2p next complete NEXT-003 --reason ... should remove the obsolete curated item from active next actions and record an audit log entry.

## Decision

# Decision - PROP-079

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner selected the hybrid generated plus curated next-action model and requested implementation.

## Date

2026-06-03

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-ca0b2e2e247f5cb8177812d3

## Decision Fingerprint

4f47baf782881dd1ac69604687c41948f14d6682103ba36dd2ae3a23451c3bca

## Lineage

None.

## Canonical Source

decision-events.yml
