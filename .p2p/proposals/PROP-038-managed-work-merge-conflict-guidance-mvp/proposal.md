# PROP-038 - Managed Work Merge Conflict Guidance MVP

## Status

`accepted`

## Problem

p2p work accept can attempt a local merge, but merge conflicts are not represented clearly in P2P state and the user does not get guided recovery commands.

## Context

Managed Work Level 5 exists. Before adding finalize, cleanup, or GitHub PR flow, accept must leave the repository and Work manifest in a clear state when a merge conflict occurs.

## Goals

- Make merge conflicts during p2p work accept explicit, inspectable, and recoverable.

## Non-Goals

- Pending.

## Proposal

Enhance p2p work accept with conflict guidance. On merge conflict, mark the Work manifest as merge_conflict, record source/base branches and conflicted files, and show recovery commands. Add p2p work accept --continue WORK-XXX to finalize after manual conflict resolution, and p2p work accept --abort WORK-XXX to abort the merge and restore the Work item to published.

## Acceptance Criteria

- Conflicting accepts do not produce ambiguous errors; Work status becomes merge_conflict with conflicted files; --continue completes the accept after conflicts are resolved; --abort aborts the merge and restores published state; tests cover conflict, continue, and abort; the skill documents the recovery flow.

## Decision

Pending.
