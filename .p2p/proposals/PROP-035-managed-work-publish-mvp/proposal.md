# PROP-035 - Managed Work Publish MVP

## Status

`accepted`

## Problem

P2P can request local review for managed Work, but it cannot yet publish the reviewed branch to the configured remote for downstream owner inspection.

## Context

Level 4.5 should be the remote handoff step between local review and owner-controlled merge. It must keep PR creation and merge separate.

## Goals

- Allow a review_requested Work item to push its managed branch to origin without opening a PR or merging.

## Non-Goals

- Pending.

## Proposal

Add p2p work publish WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status review_requested, requires a clean worktree, requires an origin remote, updates the Work manifest to published with remote branch metadata, creates a local publish metadata commit, pushes the managed branch to origin, and leaves PR and merge disabled.

## Acceptance Criteria

- A review_requested Work item can be published to origin; the command refuses wrong branches, unreviewed Work items, dirty worktrees, and missing remotes; it does not open PRs or merge; tests cover publish using a local bare remote and safety behavior; the P2P skill documents Level 4.5 separately from Level 5.

## Decision

Pending.
