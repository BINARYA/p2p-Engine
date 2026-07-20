# MCP Level 3 Proposal and Intake Draft Tools

## Provenance

- Proposal: PROP-048
- Source: .p2p/proposals/PROP-048-mcp-level-3-proposal-and-intake-draft-tools

## Problem

Agents can now initialize projects and refresh registries through MCP, but cannot create draft proposals or intake prompts without a local p2p CLI in PATH. This keeps common contribution workflows dependent on shell setup and can push agents toward stopping even for safe draft creation.

## Proposal

Add MCP tools p2p_proposal_create, p2p_intake_prompt, and p2p_intake_status. These tools may create draft proposals and intake prompts using existing core methods, and may list intake records. They must not accept, reject, defer, decide choices, apply intake recommendations, or manage work merges.

## Decision

# Decision - PROP-048

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted as MCP Level 3: safe contribution draft tools are needed after bootstrap hardening, while governance decisions remain out of MCP.

## Date

2026-05-27

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-dddd2373a3668d3c06a4c7ef

## Decision Fingerprint

1010f4c013ae49f6fb3d1cf7864632221ae066ff9242f2d11fd79d7e02d8032a

## Lineage

None.

## Canonical Source

decision-events.yml
