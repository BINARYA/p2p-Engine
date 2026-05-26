# PROP-036 - Managed Work Accept MVP

## Status

`accepted`

## Problem

P2P can publish reviewed managed Work branches, but it cannot yet perform the owner-controlled local merge that accepts a Work item into the base branch.

## Context

Level 5 should integrate published Work only through an explicit owner action, while keeping push to the base branch and branch cleanup separate.

## Goals

- Allow an owner to accept a published Work item by merging its managed branch locally into the base branch.

## Non-Goals

- Pending.

## Proposal

Add p2p work accept WORK-XXX. The command requires Work status published, a clean Git worktree, the Work branch to exist locally, and the current branch to be the manifest base branch. It performs a local no-ff merge from the managed branch, records accepted/merged metadata in the Work manifest, commits that metadata on the base branch, and leaves push and cleanup disabled.

## Acceptance Criteria

- A published Work item can be accepted into main/base locally; the command refuses unpublished Work, wrong branches, dirty worktrees, and missing Work branches; it does not push main or delete branches; tests cover accept and safety behavior; the P2P skill documents Level 5.

## Decision

Pending.
