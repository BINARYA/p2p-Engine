# PROP-088 - MCP Artifact Import Parity

## Status

`accepted`

## Problem

Real MCP testing showed a gap in the proposal artifact workflow. MCP clients can generate prompts, update structured proposal sections, and set artifact coverage state, but they cannot import or update long-form proposal artifact content such as exploration.md, findings.md, clarifications.md, or impact-map.yml through MCP. The CLI already has controlled import primitives for impact and exploration outputs, so MCP users hit a missing primitive even when the core engine can perform the write safely.

## Context

PROP-086 made artifact-aware readiness depend on public CLI or explicit MCP write tools, with no direct .p2p writes or temporary-file copying into managed proposal folders. Today MCP exposes p2p_impact_prompt and artifact state tools, but not MCP equivalents for p2p impact import, p2p explore import, or clarify/import-style content ingestion. This prevents an agent-first workflow from closing artifact gaps after it identifies them.

## Goals

- Provide MCP parity for controlled proposal artifact content imports.
- Start with existing CLI-backed impact and exploration imports, because those services and validation rules already exist.
- Keep artifact state, readiness, context, and validation consistent after imports.
- Make unsupported artifact-content mutations fail with explicit missing-primitive guidance.
- Preserve owner governance boundaries and the rule that agents never write directly under .p2p/.

## Non-Goals

- Do not add proposal acceptance, rejection, deferral, or owner decision behavior.
- Do not solve Work lifecycle MCP parity; Work publish, review, accept, finalize, and cleanup remain a separate product decision.
- Do not add provider PR/MR automation.
- Do not introduce a broad arbitrary file-write MCP tool for .p2p artifacts.

## Proposal

Add explicit write-safe MCP tools that call existing P2P Engine import services for proposal artifact content. The MVP scope covers total MCP parity with the existing controlled CLI import primitives that have fixed targets and validation: exploration imports, impact imports, clarification imports, synthesis/proposal imports, plan imports, and tasks imports. Generic arbitrary artifact import/update remains deferred until a stricter allowlist, validation model, and audit boundary are designed. MCP import tools should support both source paths and direct content payloads: source paths preserve parity with current CLI services and directory-based imports, while direct payloads support real MCP client workflows where generated content is already available in the tool call. All tools must use explicit artifact kinds, preserve existing validation behavior, return structured metadata about imported files, and keep unsupported artifact-content mutations as explicit missing-primitive errors. Documentation should describe the new MCP surface, supported artifact kinds, unsupported cases, path-vs-payload behavior, validation/audit boundaries, and the relationship between artifact content imports and artifact coverage state.

## Acceptance Criteria

- MCP exposes a controlled impact import tool that imports impact-map.yml, and related impact artifacts when supported by the existing service, without direct .p2p file writes by the agent.
- MCP exposes a controlled exploration import tool that imports exploration.md, findings.md, alternatives.md, open-questions.md, risks.md, assumptions.md, and suggested-scope.md through the existing service.
- The tools return structured imported path metadata and clear validation errors for malformed YAML or missing source content.
- After MCP artifact imports, p2p_validate succeeds and proposal readiness/context can see the updated artifacts.
- Unsupported artifact-content updates fail with explicit missing-primitive guidance and do not encourage filesystem workarounds.
- docs/MCP.md and the MCP tool catalog describe the new tools, their write-safe status, and their governance boundary.
- Tests cover successful impact import, successful exploration import, malformed impact YAML, missing source content, and the no-arbitrary-file-write boundary.

## Decision

Pending.
