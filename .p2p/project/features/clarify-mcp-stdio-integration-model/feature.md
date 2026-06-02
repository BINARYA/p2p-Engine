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

## Reason

Accepted to make MCP stdio setup and client integration semantics precise before public users rely on the install docs.

## Date

2026-05-29

## Approver

local
