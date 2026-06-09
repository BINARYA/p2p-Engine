# Changelog

All notable changes to this project should be recorded here.

This project is early-stage and did not previously maintain a public changelog.
Use this file for human-readable release notes as the repository moves toward
tagged releases.

## Unreleased

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
