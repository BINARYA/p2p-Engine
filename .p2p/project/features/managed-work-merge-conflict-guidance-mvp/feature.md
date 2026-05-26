# Managed Work Merge Conflict Guidance MVP

## Provenance

- Proposal: PROP-038
- Source: .p2p/proposals/PROP-038-managed-work-merge-conflict-guidance-mvp

## Problem

p2p work accept can attempt a local merge, but merge conflicts are not represented clearly in P2P state and the user does not get guided recovery commands.

## Proposal

Enhance p2p work accept with conflict guidance. On merge conflict, mark the Work manifest as merge_conflict, record source/base branches and conflicted files, and show recovery commands. Add p2p work accept --continue WORK-XXX to finalize after manual conflict resolution, and p2p work accept --abort WORK-XXX to abort the merge and restore the Work item to published.

## Decision

# Decision - PROP-038

## Status

`accepted`

## Outcome

accepted

## Reason

Accept/merge is the riskiest step in the managed Work lifecycle; conflicts need explicit P2P guidance before finalize or GitHub handoff.

## Date

2026-05-26

## Approver

local
