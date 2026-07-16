# Changelog

All notable changes to this project should be recorded here.

This project is early-stage and did not previously maintain a public changelog.
Use this file for human-readable release notes as the repository moves toward
tagged releases.

## Unreleased

- Target release is P2P Engine `0.3.0`. Workspace schema v1 remains operable;
  the v1-to-v2 transition is advertised only by the `0.3.x` runtime line.
- Added workspace schema v2 with a forward-only v1-to-v2 migration that moves
  legacy definition questions into one validated project-question authority.
- Added typed, bounded project-readiness gaps; persistent owner-controlled
  project-question lifecycle; deterministic fallback questions; and explicit
  vertical reconciliation.
- Added owner-confirmed atomic convergence of answered project questions into
  project definition state, including source-bound previews, exact replay,
  rollback and concurrency protection.
- Added concrete readiness next actions, descriptive question progress,
  explicit freshness impacts and inactive decision-context question metadata.
- Added CLI project-readiness gap/question/reconcile/apply workflows and bounded
  read-only MCP parity; MCP project-question writes remain intentionally absent.
- Added workspace schema versioning independent from runtime compatibility,
  deterministic legacy analysis and forward-only migration plans.
- Added owner-confirmed transactional migration apply with process-safe locking,
  candidate-overlay validation, exact rollback and interrupted recovery.
- Added atomic preview/apply primitives for project definition, bounded metadata,
  proposal vertical coverage, impact corrections and conflict-memory updates.
- Corrected legacy decision/relation parsing and introduced explicit diagnostics
  for ambiguous relations and invalid targets.
- Added independent project definition/evidence progress axes, a full
  derived-state freshness graph and owned-output reconciliation.
- Added read-only CLI/MCP inspection for schema, plans, progress, freshness and
  vertical coverage; migration apply and recovery remain CLI-only.
- Source and package metadata now report `0.3.0`. Existing workspaces must make
  the v2-capable runtime available and preview/approve their runtime-contract
  transition before schema migration; no environment change is performed
  automatically.

## 0.1.7 - 2026-06-09

- Added proposal question orchestration and artifact-aware readiness coverage
  so agents can inspect missing/weak proposal memory through CLI and MCP
  primitives.
- Added pluggable project vertical resources and project readiness review
  support for domain-specific proposal/project setup.
- Added visible project definition export flows and MCP/CLI surfaces for
  downstream project context.
- Expanded generated agent instructions, public CLI/MCP docs, validation,
  readiness, context packet, and registry coverage for the new workflows.
- Kept historical proposals advisory-compatible while initializing structured
  artifact state for new proposals by default.

## 0.1.6 - 2026-06-08

- Refined public README positioning and documentation map.
- Added practical tutorial and glossary documentation.
- Promoted CLI and MCP guides from placeholders to minimum usable guides.
- Added public repository hygiene files.
- Refactored `P2PWorkspace`, CLI commands, and MCP tools into modular services,
  handlers, registries, and command modules while preserving public behavior.
- Added local development specs and agent instructions for engineering quality
  and project-output binding workflows.
- Expanded test coverage across services, MCP handlers, branch workflows, and
  validation surfaces.
