# PROP-077 - Permission-Gated Draft Proposal Decisions via MCP

## Status

`accepted`

## Problem

MCP exposes proposal branch accept/reject but does not expose direct draft proposal accept/reject/defer decisions, so agents using MCP cannot complete owner-approved governance on draft proposals without falling back to CLI or raw state edits.

## Context

Pending.

## Goals

- Provide explicit MCP tools for owner-approved draft proposal accept, reject, and defer decisions while preserving the governance boundary through granted consent receipts.

## Non-Goals

- Pending.

## Proposal

Add p2p_proposal_accept, p2p_proposal_reject, and p2p_proposal_defer MCP tools. Each tool must require proposal_id, actor_id, consent_id, and reason, validate a granted consent receipt for operation proposal_accept/proposal_reject/proposal_defer targeting the proposal ID and actor, call the same workspace decision path used by the CLI, consume the consent with audit metadata, and document that MCP can request but not grant consent.

## Acceptance Criteria

- The CLI remains unchanged for direct owner decisions; MCP lists the new tools; requested consent cannot authorize draft decisions; granted matching consent authorizes and consumes the decision; docs and agent skill explain the distinction between draft proposal decisions and branch decisions.

## Decision

Pending.
