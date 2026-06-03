# PROP-079 - Managed Next Action Lifecycle

## Status

`accepted`

## Problem

P2P next actions can become stale because .p2p/project/next-actions.yml is curated project state but the CLI only reads it. There is no managed command to add, complete, retire, or refresh next actions, so agents either leave obsolete items such as completed consolidation tasks visible or must edit .p2p state by hand, which violates the managed-state boundary.

## Context

Pending.

## Goals

- Provide a managed hybrid next-action model that combines curated owner/agent actions with generated actions derived from project state, and expose lifecycle CLI commands so stale next actions can be closed without manual .p2p edits.

## Non-Goals

- Pending.

## Proposal

Implement a hybrid next-action lifecycle. Curated active actions remain in .p2p/project/next-actions.yml. Completed and retired curated actions are moved to .p2p/project/next-actions-log.yml with status, reason, and date. Generated actions are computed at runtime from project state using the existing fallback/blocker logic and shown alongside curated actions with clear source labels. Add CLI commands p2p next list, p2p next add, p2p next complete, p2p next retire, and p2p next refresh. The default p2p next view should list curated plus generated actions with deduplication by kind/target. p2p next complete NEXT-003 --reason ... should remove the obsolete curated item from active next actions and record an audit log entry.

## Acceptance Criteria

- Users can add curated next actions through CLI; users can complete or retire curated actions through CLI without editing .p2p files; completed/retired actions are audited in next-actions-log.yml; p2p next shows curated and generated actions together; generated actions still appear even when curated actions exist; stale curated actions such as NEXT-003 can be completed; p2p validate remains clean and tests cover add, complete, retire, generated visibility, and deduplication.

## Decision

Pending.
