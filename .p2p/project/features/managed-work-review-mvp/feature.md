# Managed Work Review MVP

## Provenance

- Proposal: PROP-034
- Source: .p2p/proposals/PROP-034-managed-work-review-mvp

## Problem

P2P can submit managed branch work as a local commit, but it cannot yet mark that submitted work as ready for owner review.

## Proposal

Add p2p work review WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status submitted, requires a clean worktree, records the commit to review, updates the Work manifest to review_requested, creates a local metadata commit, and leaves push/PR/merge disabled.

## Decision

# Decision - PROP-034

## Status

`accepted`

## Outcome

accepted

## Reason

This completes the local review-request level before remote handoff and owner merge.

## Date

2026-05-26

## Approver

local
