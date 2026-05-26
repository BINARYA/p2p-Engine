# Managed Work Publish MVP

## Provenance

- Proposal: PROP-035
- Source: .p2p/proposals/PROP-035-managed-work-publish-mvp

## Problem

P2P can request local review for managed Work, but it cannot yet publish the reviewed branch to the configured remote for downstream owner inspection.

## Proposal

Add p2p work publish WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status review_requested, requires a clean worktree, requires an origin remote, updates the Work manifest to published with remote branch metadata, creates a local publish metadata commit, pushes the managed branch to origin, and leaves PR and merge disabled.

## Decision

# Decision - PROP-035

## Status

`accepted`

## Outcome

accepted

## Reason

This adds the remote handoff step after local review while keeping PR creation and merge separate.

## Date

2026-05-26

## Approver

local
