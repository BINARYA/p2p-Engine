# PROP-075 - MCP End-To-End Proposal Collaboration Workflow

## Status

`accepted`

## Problem

MCP exposes useful proposal collaboration primitives, but a cloud or agent-only workflow is not yet end-to-end. An agent can create proposals and branches, but publish requires a consent receipt that MCP cannot request or create; remote P2P profile configuration is CLI-only; proposal drafts created through MCP leave a dirty worktree that blocks branch creation; and proposal branches can be accidentally chained from the current branch instead of a stable base branch.

## Context

Pending.

## Goals

- Make the normal proposal collaboration path coherent and closable through P2P primitives without raw Git.
- Clarify draft persistence and commit behavior after MCP proposal creation or update.
- Prevent accidental branch chaining by requiring or defaulting a safe base branch.
- Define a safe consent-request path for MCP that preserves owner approval.
- Allow MCP clients to correct remote profile metadata when policy allows it.

## Non-Goals

- Let MCP grant owner consent without an owner-controlled approval path.
- Open provider PRs/MRs automatically.
- Bypass clean-worktree requirements by silently committing arbitrary unrelated files.

## Proposal

Define an MCP end-to-end proposal collaboration workflow: create or update draft proposal, persist/commit draft state through an explicit P2P primitive or documented auto-commit policy, create a managed proposal branch from an explicit base branch such as main, request or reference owner consent, publish the branch, and request review. Add MCP tools or behavior such as p2p_project_remote_configure, p2p_consent_request, p2p_proposal_draft_commit, and p2p_proposal_branch with base_branch. Keep p2p_consent_grant owner-controlled; MCP may request consent, but granting consent should remain CLI/UI/server owner action until strong authentication exists.

## Acceptance Criteria

- A documented MCP workflow exists for create proposal -> persist draft -> branch from base -> request consent -> publish -> request review.
- p2p_proposal_branch supports explicit base_branch or refuses unsafe branch chaining from another proposal branch.
- MCP can request or record pending consent without consuming it, while grant remains owner-controlled.
- MCP can configure or request correction of P2P remote profile metadata without manual .p2p edits.
- Dirty worktree errors after proposal create/update include a precise P2P recovery command.
- Tests cover branch base guardrails, consent-request lifecycle, and remote profile correction.

## Decision

Pending.
