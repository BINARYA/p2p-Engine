# Multi-Branch Work Scan MVP

## Provenance

- Proposal: PROP-031
- Source: .p2p/proposals/PROP-031-multi-branch-work-scan-mvp

## Problem

P2P Work manifests can represent handoff plans locally, but P2P still cannot discover Work manifests that live on parallel P2P-managed branches without checking them out.

## Proposal

Add p2p work scan to read local branches matching p2p/work/* through Git plumbing, discover .p2p/work/WORK-XXX/manifest.yml files on those branches, and write an aggregated .p2p/registries/work.yml. The command must be read-only with respect to Git: no checkout, fetch, branch creation, commit, PR, or merge.

## Decision

# Decision - PROP-031

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to add read-only visibility into P2P-managed work manifests on parallel local branches.

## Date

2026-05-26

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-cd85ea1db7cd737634b466c2

## Decision Fingerprint

dc1c1a89586cd8ad2775804335284af23cc8397212891df14d90b23a0f04530c

## Lineage

None.

## Canonical Source

decision-events.yml
