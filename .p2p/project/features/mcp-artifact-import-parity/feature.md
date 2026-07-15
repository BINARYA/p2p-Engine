# MCP Artifact Import Parity

## Provenance

- Proposal: PROP-088
- Source: .p2p/proposals/PROP-088-mcp-artifact-import-parity

## Problem

Real MCP testing showed a gap in the proposal artifact workflow. MCP clients can generate prompts, update structured proposal sections, and set artifact coverage state, but they cannot import or update long-form proposal artifact content such as exploration.md, findings.md, clarifications.md, or impact-map.yml through MCP. The CLI already has controlled import primitives for impact and exploration outputs, so MCP users hit a missing primitive even when the core engine can perform the write safely.

## Proposal

Add explicit write-safe MCP tools that call existing P2P Engine import services for proposal artifact content. The MVP scope covers total MCP parity with the existing controlled CLI import primitives that have fixed targets and validation: exploration imports, impact imports, clarification imports, synthesis/proposal imports, plan imports, and tasks imports. Generic arbitrary artifact import/update remains deferred until a stricter allowlist, validation model, and audit boundary are designed. MCP import tools should support both source paths and direct content payloads: source paths preserve parity with current CLI services and directory-based imports, while direct payloads support real MCP client workflows where generated content is already available in the tool call. All tools must use explicit artifact kinds, preserve existing validation behavior, return structured metadata about imported files, and keep unsupported artifact-content mutations as explicit missing-primitive errors. Documentation should describe the new MCP surface, supported artifact kinds, unsupported cases, path-vs-payload behavior, validation/audit boundaries, and the relationship between artifact content imports and artifact coverage state.

## Decision

# Decision - PROP-088

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted by owner after resolving MCP artifact import scope toward full parity with existing controlled CLI import primitives. The MVP covers exploration, impact, clarification, synthesis/proposal, plan, and tasks imports through explicit write-safe MCP tools, supports both source paths and direct content payloads, and keeps generic unmanaged artifact import deferred. Readiness is decision_ready with score 100; remaining Q001 answered-not-applied signal is treated as a lifecycle bookkeeping anomaly because proposal.md reflects the accepted scope.

## Date

2026-07-06

## Approver

local
