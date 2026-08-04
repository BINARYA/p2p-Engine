# Requirements - Single Current Pack And Workspace Schema Baseline

## Origin

- Accepted P2P proposal: `PROP-104`.
- Owner decision: accepted by `mrjungle` on 2026-08-03.
- Target release: P2P Engine `0.4.6`.
- This is an explicitly approved breaking change for unpublished pre-release
  contracts.

## Goal

Reduce the runtime to one supported vertical-pack schema and one supported
workspace schema. Maintained resources and the canonical project must retain
their semantic content, while obsolete readers, migrations, precedence rules
and fixtures stop being part of the shipped product.

## In Scope

- Vertical pack schema `2` and portable package format `1` as the only current
  pack contracts.
- Workspace schema `3` as the only current project-memory contract.
- Conversion of all bundled vertical resources to schema 2.
- A disposable, repository-development conversion path for the canonical
  P2P Engine project when conversion is needed.
- Stable diagnostics for obsolete schemas.
- Removal of runtime compatibility branches and tests whose only purpose is
  to preserve obsolete layouts.
- Installed-wheel, CLI, MCP projection and full-suite verification.

## Out Of Scope

- General migration support for third-party projects.
- Runtime auto-migration of obsolete workspaces or packs.
- Remote registry behavior and draft authoring.
- Changes to proposal, decision or permission semantics unrelated to schema
  compatibility.

## Functional Requirements

### Current Contracts

- R001: P2P Engine 0.4.6 SHALL identify vertical pack schema 2 as the only
  supported vertical-pack schema.
- R002: P2P Engine 0.4.6 SHALL identify workspace schema 3 as the only
  supported workspace-memory schema.
- R003: Portable archives SHALL continue to use package format 1 and SHALL
  contain a valid schema-2 pack.
- R004: Every bundled vertical resource SHALL use schema 2 and a complete
  manifest with publisher, ID, semantic version and license.
- R005: Bundled pack coordinates SHALL be exact and stable across source-tree
  and installed-wheel execution.

### Failure Behavior

- R006: Loading a schema-1 vertical pack SHALL fail with stable error code
  `P2P_VERTICAL_UNSUPPORTED_SCHEMA` and identify supported schema 2.
- R007: Opening a workspace whose declared current schema is not 3 SHALL fail
  with stable error code `P2P_WORKSPACE_UNSUPPORTED_SCHEMA` before mutation.
- R008: Missing schema declarations SHALL NOT be interpreted as an obsolete
  implicit default.
- R009: Unsupported-schema failures SHALL provide a recovery message stating
  that 0.4.6 does not provide runtime legacy conversion.
- R010: Read-only status/version surfaces SHALL report workspace, vertical pack
  and package-format contracts as separate values.

### Conversion And Deletion

- R011: Any one-time canonical-project converter SHALL live outside the
  shipped runtime and SHALL require explicit source and destination roots.
- R012: A conversion SHALL write to a fresh destination and SHALL NOT mutate
  its source in place.
- R013: Conversion evidence SHALL compare canonical object counts, accepted
  decision heads, proposal identities, active vertical and validation results
  before and after conversion.
- R014: Once maintained state is current, shipped code SHALL NOT contain a
  fallback loader or automatic migration for schema-1 packs or workspace
  schemas below 3.
- R015: Project-local and bundled pack resolution SHALL use one schema-2
  validation and composition path.

### Safety And Packaging

- R016: Rejecting an obsolete pack or workspace SHALL cause zero persistent
  writes.
- R017: Packaging metadata SHALL include every converted bundled resource.
- R018: Source-tree and installed-wheel behavior SHALL resolve the same
  coordinates and semantic checksums for bundled verticals.
- R019: Documentation SHALL identify the 0.4.6 break and require WaveKit to
  rebuild worker images and recreate disposable test workspaces.

## Acceptance Criteria

- AC001: Every bundled vertical validates as schema 2 and can be packaged as a
  deterministic portable archive.
- AC002: A schema-1 pack is rejected with
  `P2P_VERTICAL_UNSUPPORTED_SCHEMA` without writes.
- AC003: A workspace declaring schema 2 is rejected with
  `P2P_WORKSPACE_UNSUPPORTED_SCHEMA` without writes.
- AC004: No maintained runtime test expects schema-1 pack or pre-v3 workspace
  operation to succeed.
- AC005: Source-tree and built-wheel smoke tests expose identical bundled
  vertical identity and checksums.
- AC006: The canonical P2P project validates with zero errors after any needed
  one-time conversion.
- AC007: Focused schema tests, public CLI/MCP tests and the full suite pass.

## Public Surface Impact

- CLI: breaking rejection of obsolete schemas; additive contract discovery.
- MCP: inherited rejection through the workspace facade; no new mutation tool.
- Storage: schema-2 packs and workspace schema 3 only.
- Docs: migration/release note and current contract documentation.
- Tests: old compatibility fixtures are converted or removed.
- Agent-facing behavior: generated setup guidance must not recommend obsolete
  runtime migration flows.

