# PROP-059 - P2PWorkspace Modular Refactoring Plan

## Status

`accepted`

## Problem

P2PWorkspace has grown into a large monolithic class that contains initialization, proposals, governance, project state, assessment, context, specs, Change Sets, Work lifecycle, registry, and Git-related behavior. This is functional for the MVP but increases cognitive load, regression risk, and difficulty for contributors.

## Context

The current repository has broad and growing surfaces: CLI, P2PWorkspace facade, filesystem storage, Git collaboration, registries, project refresh, readiness/maturity assessment, software/spec export, MCP tools, permission/consent handling, generated agent policy, and local development specs. The proposal has been refined through owner discussion: the first deliverable must be an architecture contract and development guidance, not source refactoring. P2PWorkspace should remain the compatibility facade while internal managers/services become the target home for cohesive behavior. This proposal remains in P2P governance scope; implementation tasks will be derived later through the local specs binding workflow after acceptance.

## Goals

- Approve a modular architecture direction for P2P Engine without changing runtime behavior.
- Preserve the public CLI, MCP, storage, consent, governance, and P2PWorkspace compatibility surface while extracting cohesive internal modules in later work.
- Define a layered architecture that separates domain rules, application workflows, persistence adapters, Git effects, MCP transport/schema handling, and CLI presentation.
- Create development guidance for humans and agents before non-trivial refactoring starts.
- Select consent/permissions as the preferred first future code extraction after the architecture contract is accepted and bound into local specs.

## Non-Goals

- Do not rewrite the whole engine in one pass.
- Do not implement source refactoring as part of this proposal decision.
- Do not break existing CLI commands, MCP tool names, .p2p storage layouts, validation behavior, registry refresh behavior, consent semantics, or owner-controlled governance actions.
- Do not split cli.py mechanically before service/use-case boundaries are defined.
- Do not translate this proposal into source-level implementation tasks inside specs/ until the proposal is accepted and intentionally bound.

## Proposal

Adopt a conservative modular refactoring program. P2PWorkspace remains the stable compatibility facade, but new behavior should move into dedicated services and adapters. cli.py, storage/filesystem.py, and mcp/tools.py become thinner orchestration/facade layers rather than the default home for new domain logic. The first deliverable is documentation and development contract only: update AGENTS.md with short non-negotiable agent rules, create docs/DEVELOPMENT-GUIDELINES.md as the full architecture guide, and define a prioritized refactoring roadmap. Alternatives considered are: keep the monolith and document conventions; split large files mechanically; introduce internal managers behind the stable P2PWorkspace facade; or redesign public APIs. The preferred option is internal managers behind the facade because it improves maintainability while preserving CLI, MCP, storage, governance, and agent compatibility. After acceptance and local specs binding, the recommended first code extraction is consent/permissions because it has a clear boundary, high safety value, lower presentation exposure than CLI, and can establish the extraction pattern before more central proposal/readiness workflows are touched. Services/use cases should be extracted before CLI modularization. Any breaking change requires a separate proposal.

## Acceptance Criteria

- The proposal explicitly defines P2PWorkspace as a compatibility facade, not the long-term home for all behavior.
- The proposal identifies cli.py, storage/filesystem.py, and mcp/tools.py as compatibility/orchestration layers that should not receive unrelated new domain logic by default.
- The proposal chooses internal managers behind the stable facade over monolith-only documentation, mechanical split, or public API redesign.
- The first accepted deliverable is an architecture contract: AGENTS.md agent rules, docs/DEVELOPMENT-GUIDELINES.md, and a prioritized roadmap, with no runtime behavior change.
- The proposal records compatibility constraints for CLI commands, MCP tool names and payloads, .p2p storage artifacts, validation, registry refresh, consent receipts, Git/sync behavior, and owner-controlled governance.
- The proposal records consent/permissions as the preferred first future code extraction after accepted-proposal binding into local specs.
- The proposal requires service/use-case extraction before CLI modularization.
- The proposal identifies impact and overlap with permission-gated MCP governance, draft proposal decisions via MCP, next actions MCP/skill support, domain-aware project export, runtime bootstrap, and the local specs binding workflow.
- No source refactor is required merely to accept the proposal; implementation tasks are produced later through the local specs binding workflow.

## Decision

Pending.
