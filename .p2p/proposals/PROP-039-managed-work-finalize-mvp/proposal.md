# PROP-039 - Managed Work Finalize MVP

## Status

`accepted`

## Problem

After p2p work accept, the base branch merge remains local and P2P has no command to publish that accepted state to the remote.

## Context

Managed Work now supports plan, branch, submit, review, publish, accept, status, and merge conflict guidance. Finalize should be the explicit post-accept publication step, separate from cleanup and PR creation.

## Goals

- Allow an owner to finalize an accepted Work item by pushing the base branch to the configured remote.

## Non-Goals

- Pending.

## Proposal

Add p2p work finalize WORK-XXX. The command requires Work status accepted, the current branch to match the Work base branch, a clean worktree, and a configured remote. It updates the Work manifest to finalized, records remote/base metadata, creates a local finalize metadata commit, pushes the base branch to the remote, and leaves branch cleanup disabled.

## Acceptance Criteria

- An accepted Work item can be finalized to origin/main or another configured base branch; the command refuses unaccepted Work, wrong branches, dirty worktrees, and missing remotes; it does not delete local or remote Work branches; tests cover finalize and safety behavior; the skill documents finalize after accept.

## Decision

Pending.
