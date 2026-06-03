# MCP End-To-End Proposal Collaboration Workflow

## Provenance

- Proposal: PROP-075
- Source: .p2p/proposals/PROP-075-mcp-end-to-end-proposal-collaboration-workflow

## Problem

MCP exposes useful proposal collaboration primitives, but a cloud or agent-only workflow is not yet end-to-end. An agent can create proposals and branches, but publish requires a consent receipt that MCP cannot request or create; remote P2P profile configuration is CLI-only; proposal drafts created through MCP leave a dirty worktree that blocks branch creation; and proposal branches can be accidentally chained from the current branch instead of a stable base branch.

## Proposal

Define an MCP end-to-end proposal collaboration workflow: create or update draft proposal, persist/commit draft state through an explicit P2P primitive or documented auto-commit policy, create a managed proposal branch from an explicit base branch such as main, request or reference owner consent, publish the branch, and request review. Add MCP tools or behavior such as p2p_project_remote_configure, p2p_consent_request, p2p_proposal_draft_commit, and p2p_proposal_branch with base_branch. Keep p2p_consent_grant owner-controlled; MCP may request consent, but granting consent should remain CLI/UI/server owner action until strong authentication exists.

## Decision

# Decision - PROP-075

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to close the MCP proposal collaboration workflow discovered during dogfooding: MCP can now configure remote profile metadata, commit proposal drafts, branch from an explicit safe base, request owner consent without granting it, and then use existing permission-gated publish/review tools once owner consent is granted.

## Date

2026-06-03

## Approver

local
