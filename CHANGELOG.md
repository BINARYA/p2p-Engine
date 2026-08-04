# Changelog

All notable changes to this project should be recorded here.

This project is early-stage and did not previously maintain a public changelog.
Use this file for human-readable release notes as the repository moves toward
tagged releases.

## 0.4.6 - Unreleased

- Converted all four bundled verticals to schema 2 with exact
  `binarya/...@2.0.0` coordinates, licenses and checksum-bound structural
  dependencies.
- Added `p2p version` with distinct engine, CLI, workspace, vertical-pack and
  portable-package contract versions.
- Added the initial top-level `p2p vertical` local catalog and registry
  configuration commands using project-external `P2P_HOME`/platform storage,
  HTTPS validation and no implicit network access.
- Applied the shared `p2p-cli/v1` success/error envelope to all 109 commands
  supporting JSON, with command-path operation IDs, JSON parser failures and
  stable exit classes for invalid requests, conflicts, authorization and
  unavailable dependencies.
- Added caller-keyed idempotency for vertical install, adopt and migrate apply,
  with hashed durable receipts committed in the same atomic transaction, exact
  replay, conflict/drift detection and redacted `p2p mutation status` recovery
  lookup.
- Made vertical-pack schema 2 and workspace schema 3 the only runtime-supported
  contracts. Removed schema-1 pack loading, flat candidate add/propose flows,
  workspace conversion services, migration CLI commands, and migration MCP
  planning.
- Added stable `P2P_VERTICAL_UNSUPPORTED_SCHEMA` and
  `P2P_WORKSPACE_UNSUPPORTED_SCHEMA` failures with no-write behavior for
  unsupported contracts.
- Retained atomic governed-write safety as schema-independent workspace
  transaction infrastructure under `.p2p/.internal/workspace-transactions/`,
  with explicit owner-confirmed CLI status, rollback, and resume commands.
- Converted the canonical P2P Engine project to
  `binarya/software_project@2.0.0` and workspace schema 3 while preserving its
  project-definition evidence and historical schema audit records.
- WaveKit must rebuild its P2P worker image for 0.4.6 and recreate disposable
  development/test workspaces that use an older workspace or pack schema.
- Added provider-neutral remote search, pull, OAuth device authentication,
  immutable user caching and authenticated exact-artifact publication.
- Added normalized vertical drafts with optimistic updates, explicit fork,
  previous-release and structural lineage, atomic materialization, bound
  validation/package evidence, immutable local add and WaveKit JSON fixtures.
- Added stable no-section installation and proposal-target guards shared by
  CLI and MCP, plus deterministic bundled-pack and 0.4.6 wheel/sdist checks.

## 0.4.5 - 2026-08-02

- Corrected portable vertical resolution so valid hyphenated schema-v2 IDs
  retain their exact spelling across init, adoption, migration and later reads.
- Made the exact locked coordinate authoritative for active sections,
  definition state, readiness, validation and existing MCP read tools.
- Added fail-closed ambiguity and coordinate-conflict errors for side-by-side
  portable versions while preserving schema-v1 and bundled source precedence.
- Strengthened pre-commit active, lock and definition identity validation and
  aligned schema-v2 directory validation with portable archive validation.
- Added WaveKit-facing regressions for direct init, adopt, migrate, exact
  inheritance, side-by-side versions and installed-wheel behavior.

## 0.4.4 - 2026-08-02

- Added deterministic portable vertical-pack schema v2 artifacts with exact
  publisher, version, license, lineage and dependency-checksum contracts.
- Added governed install, adoption and evidence-preserving migration through
  state-bound CLI preview/apply operations and stable JSON envelopes.
- Added project initialization from a local vertical artifact with checksum
  preflight, side-by-side exact versions and explicit migration orphans.
- Kept registry discovery and artifact delivery outside P2P Engine so server
  products such as WaveKit can enforce their own catalog and authorization
  policies while P2P remains deterministic and offline.
- Removed the canonical P2P project-design workspace from the implementation
  repository and retained implementation specifications locally under `specs/`.
- Corrected concurrent readiness convergence classification so changed
  preconditions report `stale_preview` instead of a generic failure.

## 0.4.3 - 2026-07-23

- Made publication CLI documentation tests independent from ANSI styling in
  GitHub Actions while preserving the same semantic option assertions.

## 0.4.2 - 2026-07-23

- Completed the proposal decision revision, revocation, reinstatement and typed
  lineage lifecycle, including schema-v3 historical decision alignment and
  concurrent-decision diagnostics.
- Added deterministic vertical project memory with full and incremental
  refresh, source fingerprints, section-oriented retrieval and bounded fast
  read paths.
- Added evidence-driven multilingual project publication with language-specific
  editions, editorial models, evidence accounting, validation and neutral PDF
  rendering.
- Added per-spec semantic provenance refresh and aligned generated project,
  registry, assessment, context and publication artifacts with the current
  source state.
- Added a descriptive current-state codebase architecture snapshot under
  `docs/development/`.

## 0.4.1 - 2026-07-19

- Added a read-only, source-bound owner-attestation template for workspace
  schema v2-to-v3 migration plans, allowing unambiguous legacy accepted
  decisions to become initial events without weakening unresolved evidence.
- Added closed and bounded attestation input validation, duplicate-key-safe YAML
  loading, exact owner/source/status/date binding, structured
  accepted-with-changes conditions and plan/apply stale-source protection.
- Preserved manual review for divergent, incomplete or lineage-dependent legacy
  authority instead of fabricating proposal decisions or relationships.
- Hardened concurrent proposal decision preview/apply and recovery behavior so
  stale competing writes fail without deleting or replacing the winning event.
- Expanded release artifact checks to require the attestation and concurrency
  implementation and their regression tests in the wheel and source
  distribution.

## 0.4.0 - 2026-07-18

- The immutable `v0.3.0` tag failed its minimum-Python release gate and
  produced no GitHub Release or published package; it is not reused or treated
  as an available runtime.
- Added workspace schema v3 with append-only proposal decision event ledgers,
  deterministic proposal/decision projections and a forward-only v2-to-v3
  migration that preserves unresolved legacy evidence.
- Added owner-governed proposal decision status, history, impact,
  preview/apply, revocation, reinstatement, lineage, projection repair, ledger
  repair and unknown-legacy resolution.
- Replaced one-step proposal decision writes with token-bound two-phase CLI and
  MCP workflows. MCP consent is bound to `PROP-XXX@preview-token`; old
  accept/reject/defer consent cannot write schema-v3 events.
- Converged proposal, registry, Change, Work, software-spec, project,
  publication and decision-context consumers on lifecycle authority while
  preserving historical rationale and reporting dependent remediation without
  mutating downstream lifecycles.
- Fixed Python 3.11 parsing of nearby-decision-context prompt fallbacks while
  preserving the rendered Explore, Impact and Synthesize output.
- Workspace schema v1 remains operable; the v1-to-v2 transition is advertised
  only by the `0.3.x` runtime line.
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
- Source and package metadata now report `0.3.1`. Existing workspaces must make
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
