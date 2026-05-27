# Draft Proposal Next Action and Agent Explanation Guard

## Provenance

- Proposal: PROP-051
- Source: .p2p/proposals/PROP-051-draft-proposal-next-action-and-agent-explanation-guard

## Problem

After MCP creates a draft proposal, p2p next can still fall back to generic project status instead of pointing the owner or agent at the draft proposal. Agent instructions also do not explicitly require show/read commands before explaining existing P2P artifacts.

## Proposal

Update fallback next actions to recommend reviewing the first draft proposal when no stronger action exists. Update generated AGENTS.md, Codex project skill, Claude instructions, .p2p/agent-policy.yml, and the repository P2P skill so agents must use proposal/choice/change/work show or MCP equivalents before explaining existing artifacts.

## Decision

# Decision - PROP-051

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted to tighten the observed MCP test behavior: draft proposals should produce useful next actions, and explanations should be grounded in show/read tools.

## Date

2026-05-27

## Approver

local
