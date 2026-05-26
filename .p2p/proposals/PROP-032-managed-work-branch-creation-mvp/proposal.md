# PROP-032 - Managed Work Branch Creation MVP

## Status

`accepted`

## Problem

P2P Work manifests can plan downstream work but cannot yet create an isolated managed branch for implementation.

## Context

The project policy keeps Git invisible to the user while using managed work branches under the hood to avoid divergence on main.

## Goals

- Allow an owner or agent to explicitly create a P2P-managed branch for a planned Work item without committing, submitting, or merging.

## Non-Goals

- Pending.

## Proposal

Add p2p work branch WORK-XXX. The command validates a clean Git repository, reads the Work manifest branch name, creates and checks out the managed branch, updates the manifest to branched, and keeps commit/merge actions disabled.

## Acceptance Criteria

- A planned Work item can be branched with p2p work branch WORK-XXX; the command refuses dirty worktrees and existing branches; tests cover branch creation and safety failures; the P2P skill documents the workflow.

## Decision

Pending.
