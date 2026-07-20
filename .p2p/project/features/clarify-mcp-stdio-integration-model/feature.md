# Clarify MCP Stdio Integration Model

## Provenance

- Proposal: PROP-069
- Source: .p2p/proposals/PROP-069-clarify-mcp-stdio-integration-model

## Problem

The installation and MCP documentation show client setup commands but do not explain that MCP stdio is not a shared server process. Users may misunderstand how multiple agents connect to P2P, where shared state lives, and when Streamable HTTP would be needed.

## Proposal

Update docs/INSTALL.md and docs/MCP.md with a clear MCP stdio model, verified client setup sections, and explicit notes about future Streamable HTTP for shared long-running multi-client services. Keep all examples based on the current Python MCP server command and --root target-project argument.

## Decision

# Decision - PROP-069

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted to make MCP stdio setup and client integration semantics precise before public users rely on the install docs.

## Date

2026-05-29

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-1c74a1b02b4379e2915f4854

## Decision Fingerprint

652a03997166b328844ce8c6fbaddab6c972fa2091aa3d4dd3e66419a19f3fee

## Lineage

None.

## Canonical Source

decision-events.yml
