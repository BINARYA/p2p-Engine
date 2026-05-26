# PROP-030 - Managed Work and Multi-Branch Visibility Policy

## Status

`accepted`

## Problem

P2P is moving toward managed Git under the hood, but users still lack a P2P-native work abstraction that can represent future branch, commit, review, and merge operations without exposing Git as the user interface.

## Context

CHANGE-001 established managed Git as an internal adapter. CHANGE-012 through CHANGE-015 created a spec/export/validate pipeline. The next step is to define work manifests and the incremental path toward invisible managed Git.

## Goals

- Define a level-based managed Git policy and implement the first safe step: read-only handoff planning through P2P Work manifests.

## Non-Goals

- Pending.

## Proposal

Introduce P2P Work as the user-facing abstraction over future Git branches. Define levels from advisory to handoff plan, managed branch, managed commit, managed review, and owner-controlled merge. Implement p2p work plan/list/show to create and inspect .p2p/work/WORK-XXX/manifest.yml for validated spec exports. This first MVP must not create branches, commits, PRs, or merges.

## Acceptance Criteria

- p2p work plan --change CHANGE-XXX --target TARGET creates a WORK manifest with source Change Set, export target, validation status, logical branch name, allowed files, and disabled auto_branch/auto_commit/auto_merge policy. p2p work list and p2p work show inspect manifests. Skill guidance explains that Git remains invisible and future levels will add branch scan/create/submit/accept incrementally.

## Decision

Pending.
