# MCP and Skill Support for Managed Next Actions

## Provenance

- Proposal: PROP-081
- Source: .p2p/proposals/PROP-081-mcp-and-skill-support-for-managed-next-actions

## Problem

The CLI now supports managed next-action lifecycle commands, but the agent skill and MCP surface still describe p2p_next as read-only/advisory only. Agents using MCP cannot add, complete, retire, or refresh curated next actions, and agents following the skill may not know the CLI lifecycle exists.

## Proposal

Add MCP tools p2p_next_add, p2p_next_complete, p2p_next_retire, and p2p_next_refresh. Treat these as write-safe project planning tools without consent receipts because they update the operational next-action board and audit completed/retired entries, but do not decide proposals, merge branches, publish remotes, or change governance policy. Update the p2p-engine skill and MCP documentation to explain that p2p_next remains read/list, while the new tools manage curated next actions. Keep owner-controlled governance boundaries intact.

## Decision

# Decision - PROP-081

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner requested MCP and skill alignment for the newly implemented managed next-action lifecycle.

## Date

2026-06-03

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-4f801b7836715b90ed233095

## Decision Fingerprint

5376442856142dc38457b2084f994ed57087b910bc476961d86aacf4f43d4721

## Lineage

None.

## Canonical Source

decision-events.yml
