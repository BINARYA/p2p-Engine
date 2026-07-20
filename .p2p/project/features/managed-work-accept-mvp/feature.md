# Managed Work Accept MVP

## Provenance

- Proposal: PROP-036
- Source: .p2p/proposals/PROP-036-managed-work-accept-mvp

## Problem

P2P can publish reviewed managed Work branches, but it cannot yet perform the owner-controlled local merge that accepts a Work item into the base branch.

## Proposal

Add p2p work accept WORK-XXX. The command requires Work status published, a clean Git worktree, the Work branch to exist locally, and the current branch to be the manifest base branch. It performs a local no-ff merge from the managed branch, records accepted/merged metadata in the Work manifest, commits that metadata on the base branch, and leaves push and cleanup disabled.

## Decision

# Decision - PROP-036

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

This completes the local owner-controlled managed Work lifecycle before optional base-branch push and cleanup.

## Date

2026-05-26

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-7c794d01387ecaff9a687116

## Decision Fingerprint

d33f79f3ade5d6126c093a6bf23390afe99784bf2205ae35af88709c07c61216

## Lineage

None.

## Canonical Source

decision-events.yml
