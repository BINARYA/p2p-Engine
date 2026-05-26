# PROP-033 - Managed Work Submit MVP

## Status

`accepted`

## Problem

P2P can create managed branches for Work items, but it cannot yet package completed branch work into an auditable managed commit.

## Context

The managed Git path should keep Git under the hood while giving the owner a clear Work lifecycle before later review and merge steps.

## Goals

- Allow a branched Work item to be submitted as a local managed commit without pushing or merging.

## Non-Goals

- Pending.

## Proposal

Add p2p work submit WORK-XXX. The command verifies the current branch is the Work branch, validates that the Work item is branched, requires changed files, records the changed file list, updates the Work manifest to submitted, stages the Work branch changes, and creates a local commit with a P2P-standard message.

## Acceptance Criteria

- A branched Work item can be submitted into one local commit; the command refuses wrong branches, unbranched Work items, and empty submissions; it does not push or merge; tests cover submit and safety behavior; the P2P skill documents Level 3.

## Decision

Pending.
