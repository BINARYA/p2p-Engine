# Managed Work Retire MVP

## Provenance

- Proposal: PROP-043
- Source: .p2p/proposals/PROP-043-managed-work-retire-mvp

## Problem

Obsolete planned Work manifests can remain in project status even after their source Change Set or export has already been completed, causing stale next actions.

## Proposal

Add p2p work retire WORK-XXX --reason TEXT. The command requires Work status planned, updates the manifest status to retired, records retirement metadata, and makes p2p work status report no next action for retired Work.

## Decision

# Decision - PROP-043

## Status

`accepted`

## Outcome

accepted

## Reason

Obsolete planned Work manifests should be retired through an explicit metadata-only command instead of manual manifest edits.

## Date

2026-05-27

## Approver

local
