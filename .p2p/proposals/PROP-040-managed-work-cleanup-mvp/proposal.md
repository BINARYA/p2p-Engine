# PROP-040 - Managed Work Cleanup MVP

## Status

`accepted`

## Problem

After p2p work finalize, managed Work branches remain locally and remotely, and P2P has no explicit owner-controlled cleanup step.

## Context

The managed Work lifecycle now reaches finalization. Cleanup should be separate from finalize so branch deletion remains explicit and reversible by policy.

## Goals

- Allow an owner to clean up finalized Work branches without changing accepted project content.

## Non-Goals

- Pending.

## Proposal

Add p2p work cleanup WORK-XXX. The command requires Work status finalized, a clean worktree, and the current branch to be the Work base branch. It deletes the local managed Work branch by default, can delete the remote Work branch with an explicit --remote flag, records cleanup metadata in the Work manifest, creates a local cleanup metadata commit, and optionally pushes the base branch so cleanup state is persisted remotely.

## Acceptance Criteria

- A finalized Work item can be cleaned locally; remote branch deletion only happens with --remote; the command refuses unfinalized Work, wrong branches, dirty worktrees, and missing branches; tests cover local cleanup, remote cleanup, and safety behavior; the skill documents cleanup after finalize.

## Decision

Pending.
