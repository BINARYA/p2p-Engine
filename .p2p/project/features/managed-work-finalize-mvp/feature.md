# Managed Work Finalize MVP

## Provenance

- Proposal: PROP-039
- Source: .p2p/proposals/PROP-039-managed-work-finalize-mvp

## Problem

After p2p work accept, the base branch merge remains local and P2P has no command to publish that accepted state to the remote.

## Proposal

Add p2p work finalize WORK-XXX. The command requires Work status accepted, the current branch to match the Work base branch, a clean worktree, and a configured remote. It updates the Work manifest to finalized, records remote/base metadata, creates a local finalize metadata commit, pushes the base branch to the remote, and leaves branch cleanup disabled.

## Decision

# Decision - PROP-039

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Finalize is the explicit post-accept publication step and keeps base-branch push separate from cleanup and PR creation.

## Date

2026-05-26

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-6dbcb4f70fe2e021423de998

## Decision Fingerprint

c7810ee5065c61e6c2790dad8578ac465cf4a7636892acebaf91f34fa381e13f

## Lineage

None.

## Canonical Source

decision-events.yml
