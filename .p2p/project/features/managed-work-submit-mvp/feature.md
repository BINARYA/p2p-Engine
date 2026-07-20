# Managed Work Submit MVP

## Provenance

- Proposal: PROP-033
- Source: .p2p/proposals/PROP-033-managed-work-submit-mvp

## Problem

P2P can create managed branches for Work items, but it cannot yet package completed branch work into an auditable managed commit.

## Proposal

Add p2p work submit WORK-XXX. The command verifies the current branch is the Work branch, validates that the Work item is branched, requires changed files, records the changed file list, updates the Work manifest to submitted, stages the Work branch changes, and creates a local commit with a P2P-standard message.

## Decision

# Decision - PROP-033

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

This is the next incremental managed Git level: local auditable submit without push or merge.

## Date

2026-05-26

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-e8c2adf067d885127c043be3

## Decision Fingerprint

116e7c110265d72d9e77942d717684a0d0c3fd79951b9135985cb90e36b4cb77

## Lineage

None.

## Canonical Source

decision-events.yml
