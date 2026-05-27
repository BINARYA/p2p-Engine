# PROP-051 - Draft Proposal Next Action and Agent Explanation Guard

## Status

`accepted`

## Problem

After MCP creates a draft proposal, p2p next can still fall back to generic project status instead of pointing the owner or agent at the draft proposal. Agent instructions also do not explicitly require show/read commands before explaining existing P2P artifacts.

## Context

The La scatola perfetta MCP test created a correct draft proposal, but next action remained weak. The agent explanation was good, but it should be anchored to current P2P state rather than conversation memory.

## Goals

- Make draft proposals visible as actionable next steps and require agents to read existing artifacts before explaining them.

## Non-Goals

- Pending.

## Proposal

Update fallback next actions to recommend reviewing the first draft proposal when no stronger action exists. Update generated AGENTS.md, Codex project skill, Claude instructions, .p2p/agent-policy.yml, and the repository P2P skill so agents must use proposal/choice/change/work show or MCP equivalents before explaining existing artifacts.

## Acceptance Criteria

- p2p next suggests review_draft_proposal for draft proposals after registries are fresh and no stronger fallback exists; generated agent policy contains an explain_existing_artifacts rule; generated agent instructions mention reading via show/MCP before explaining; tests cover the new fallback and generated policy text.

## Decision

Pending.
