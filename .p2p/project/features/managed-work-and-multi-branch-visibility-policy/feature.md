# Managed Work and Multi-Branch Visibility Policy

## Provenance

- Proposal: PROP-030
- Source: .p2p/proposals/PROP-030-managed-work-and-multi-branch-visibility-policy

## Problem

P2P is moving toward managed Git under the hood, but users still lack a P2P-native work abstraction that can represent future branch, commit, review, and merge operations without exposing Git as the user interface.

## Proposal

Introduce P2P Work as the user-facing abstraction over future Git branches. Define levels from advisory to handoff plan, managed branch, managed commit, managed review, and owner-controlled merge. Implement p2p work plan/list/show to create and inspect .p2p/work/WORK-XXX/manifest.yml for validated spec exports. This first MVP must not create branches, commits, PRs, or merges.

## Decision

# Decision - PROP-030

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to introduce P2P Work as the user-facing abstraction for the incremental path toward invisible managed Git.

## Date

2026-05-26

## Approver

local
