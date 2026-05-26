# PROP-034 - Managed Work Review MVP

## Status

`accepted`

## Problem

P2P can submit managed branch work as a local commit, but it cannot yet mark that submitted work as ready for owner review.

## Context

Level 4 should prepare the review handoff while keeping remote push, PR creation, and merge out of scope until later levels.

## Goals

- Allow a submitted Work item to enter a local review_requested state with a clear review commit and no remote side effects.

## Non-Goals

- Pending.

## Proposal

Add p2p work review WORK-XXX. The command verifies the current branch matches the Work branch, requires Work status submitted, requires a clean worktree, records the commit to review, updates the Work manifest to review_requested, creates a local metadata commit, and leaves push/PR/merge disabled.

## Acceptance Criteria

- A submitted Work item can request local review; the command refuses wrong branches, unsubmitted Work items, and dirty worktrees; it does not push, open PRs, or merge; tests cover review and safety behavior; the P2P skill documents the full Level 1-4 flow and the future 4.5/5 steps.

## Decision

Pending.
