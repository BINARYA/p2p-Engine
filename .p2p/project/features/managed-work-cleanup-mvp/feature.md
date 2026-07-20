# Managed Work Cleanup MVP

## Provenance

- Proposal: PROP-040
- Source: .p2p/proposals/PROP-040-managed-work-cleanup-mvp

## Problem

After p2p work finalize, managed Work branches remain locally and remotely, and P2P has no explicit owner-controlled cleanup step.

## Proposal

Add p2p work cleanup WORK-XXX. The command requires Work status finalized, a clean worktree, and the current branch to be the Work base branch. It deletes the local managed Work branch by default, can delete the remote Work branch with an explicit --remote flag, records cleanup metadata in the Work manifest, creates a local cleanup metadata commit, and optionally pushes the base branch so cleanup state is persisted remotely.

## Decision

# Decision - PROP-040

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Cleanup is the explicit post-finalize branch housekeeping step and keeps branch deletion separate from accept/finalize.

## Date

2026-05-27

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-5f2ffd8e9c7c485100b28d88

## Decision Fingerprint

b3cfc57fd3a86a07c97adb01f4ead40d5b23da4f588e4f4a8985a92ce75f8124

## Lineage

None.

## Canonical Source

decision-events.yml
