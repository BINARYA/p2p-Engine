# PROP-098 - Test Impact and Validation Routing

## Status

`draft`

## Problem

P2P Engine agents and maintainers currently have marker-based test tiers, but they still need a deterministic way to decide which tests are required after a specific code change. Without explicit routing from changed areas to validation tiers, agents may either run too little and miss regressions or run the full suite unnecessarily after small localized changes.

## Context

The project already has focused, public, smoke, and full validation scripts, central pytest markers, docs/TESTING.md, and a test quality policy. The missing layer is not more raw test structure and not code coverage percentage. The missing layer is an explicit, reproducible impact map: changed files or responsibilities -> affected public surfaces and risk classes -> required test commands. Code coverage may later help audit this map, but routing must be primarily explicit and deterministic because coverage does not understand public contracts, persisted schemas, MCP payloads, Git side effects, governance invariants, or logical dependencies.

## Goals

- Define deterministic test routing from changed code areas to required validation tiers.
- Give agents and maintainers a reproducible explanation for why specific tests are required or why the full suite is not necessary.
- Escalate to broader validation when public contracts, persistence, MCP, Git, governance, shared services, or uncertainty are involved.
- Keep the existing focused, public, smoke, and full validation tiers as the execution primitives.

## Non-Goals

- Do not replace pytest markers or the existing validation scripts.
- Do not rely solely on code coverage to infer test impact.
- Do not eliminate full-suite validation before releases, broad refactors, merges, or uncertain-impact changes.
- Do not implement CI provider automation in the first proposal unless later accepted through implementation planning.

## Proposal

Introduce a Test Impact and Validation Routing model for P2P Engine. The model should map repository areas such as services, CLI command modules, MCP catalogs and handlers, storage/facade code, Git adapters, generated artifact flows, docs, and tests to required validation tiers and representative test targets. The routing should include escalation rules for public CLI/MCP behavior, persisted file schemas, registry or validation behavior, Git/sync/branch side effects, permission or governance semantics, and broad refactors. When impact is uncertain, the route must fall back conservatively to public-contract or full validation. The system should surface a readable rationale, for example: changed files, inferred areas, required commands, skipped broader tiers, and the reason a full suite is or is not needed.

## Acceptance Criteria

- A documented routing table maps major source and documentation areas to focused, public, smoke, git, integration, or full validation expectations.
- Routing rules identify when CLI tests, MCP tests, Git/integration tests, or full-suite validation are required.
- The routing model includes a conservative fallback for unknown, cross-cutting, persistence, governance, permission, or public-contract changes.
- Agent-facing instructions are updated so agents report the selected test scope and rationale before or after validation.
- The model keeps full-suite validation required before release, merge, broad refactor completion, or unresolved impact.
- Coverage remains optional diagnostic input and is not used as the sole source of routing truth.

## Decision

Pending.
