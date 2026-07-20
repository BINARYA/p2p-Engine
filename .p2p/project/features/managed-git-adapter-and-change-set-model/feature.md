# Managed Git Adapter and Change Set Model

## Provenance

- Proposal: PROP-013
- Source: .p2p/proposals/PROP-013-change-set-and-git-branch-model

## Problem

P2P Engine distinguishes proposals from project state, but it does not yet define how accepted decisions become operational change sets or how Git operations should be managed under the hood without exposing branch/commit/merge complexity to users.

## Proposal

Adopt a managed Git model: proposals and change sets are the public P2P concepts, while Git branches, commits, merges, and tags are internal operations selected by a configurable policy. Git details are visible only in verbose/debug modes.

## Decision

# Decision - PROP-013

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Current owner confirms the historical acceptance of PROP-013 for the Managed Git Under The Hood model, with Change Set as the visible operational unit and Git as the internal persistence, audit, synchronization, and collaboration adapter. The MVP remained metadata-only, hid Git details by default, disabled automatic commits, branches, and tags, and required Change Sets to originate from accepted proposals or decisions.

## Date

2026-05-26

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-20b6debbe45862ae86007979

## Decision Fingerprint

0e72530b61916bbb95fb093adf375a31c222dfd14b72db465e2d0d75c302b009

## Lineage

None.

## Canonical Source

decision-events.yml
