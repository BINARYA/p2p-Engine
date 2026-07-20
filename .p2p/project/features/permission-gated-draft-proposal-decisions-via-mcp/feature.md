# Permission-Gated Draft Proposal Decisions via MCP

## Provenance

- Proposal: PROP-077
- Source: .p2p/proposals/PROP-077-permission-gated-draft-proposal-decisions-via-mcp

## Problem

MCP exposes proposal branch accept/reject but does not expose direct draft proposal accept/reject/defer decisions, so agents using MCP cannot complete owner-approved governance on draft proposals without falling back to CLI or raw state edits.

## Proposal

Add p2p_proposal_accept, p2p_proposal_reject, and p2p_proposal_defer MCP tools. Each tool must require proposal_id, actor_id, consent_id, and reason, validate a granted consent receipt for operation proposal_accept/proposal_reject/proposal_defer targeting the proposal ID and actor, call the same workspace decision path used by the CLI, consume the consent with audit metadata, and document that MCP can request but not grant consent.

## Decision

# Decision - PROP-077

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner requested this refinement after real MCP usage exposed that draft proposal rejection was not available as a permission-gated MCP operation.

## Date

2026-06-03

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-5a6828b39348afde1ac4057c

## Decision Fingerprint

2a9ab636534612f64008d5e2db899f043dae64493f8b6fefb6a16b36f412d8c1

## Lineage

None.

## Canonical Source

decision-events.yml
