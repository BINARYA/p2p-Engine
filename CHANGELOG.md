# Changelog

All notable changes to this project should be recorded here.

This project is early-stage and did not previously maintain a public changelog.
Use this file for human-readable release notes as the repository moves toward
tagged releases.

## Unreleased

- Clarified that `remote-only` is a WaveKit-owned access mode with no
  client-local P2P root or generated integration artifacts, and made local
  renderers reject it fail-closed instead of falling through to local-profile
  assumptions.
- Aligned the maintained WaveKit transition handoff with its current 0.6.4
  fixture manifest and described GitHub publication accurately as create-only,
  attested and checksum-pinned rather than GitHub-enforced immutable.

## 0.6.4 - 2026-09-05

- Completed linked-project lifecycle operations for suspend/resume, verified
  detach with a new project identity and lineage policy, create-as-new,
  immutable publication, local-replica removal, remote archive/restore and
  receipt-gated remote deletion.
- Added backend-neutral linked-replica drift detection using canonical identity,
  revision and semantic/blob digests while ignoring formatting, Git state and
  valid adapter-owned transient bytes.
- Added fail-closed sync fencing, bounded sanitized semantic diff, verified
  forensic backup and authoritative snapshot rebuild with atomic activation.
- Added owner-confirmed reconciliation of a complete recognized domain intent
  through ordinary WaveKit commands, with stale-plan protection and idempotent
  recovery after a lost response.
- Exposed lifecycle and drift inspection through approved read-only MCP tools
  while keeping destructive recovery and reconciliation apply on the owner CLI.
- Updated generated agent instructions so linked-local agents stop writes on
  drift and direct the owner to governed recovery instead of editing `.p2p` or
  using Git as a merge mechanism.
- Replaced duplicate main/tag release qualification with a lightweight
  single-job main CI and an explicit on-demand release workflow that creates
  the tag only after the complete candidate, cross-platform and attestation
  gates pass.

## 0.6.3 - 2026-09-04

- Added typed linked-project commands, immutable idempotent operation receipts,
  monotone project revisions and backend-neutral after-state change batches.
- Added cursor-based durable feed replay, retention-gap snapshot fallback,
  verified blob prefetch and atomic local batch/inbox/cursor application.
- Added `p2p sync status|catch-up|recover` and `p2p watch`, with SSE used only
  as an optional wake-up over the authoritative HTTP recovery path.
- Routed linked MCP reads through freshness catch-up and linked MCP domain
  mutations through WaveKit with operation, revision and entity-precondition
  evidence; raw feed/cursor/storage primitives remain private.
- Updated generated `linked-local` agent instructions and capability policy;
  offline mutations remain blocked and presence stays ephemeral and excluded
  from project memory and portable bundles.

## 0.6.2 - 2026-09-03

- Added governed transfer of a standalone project's canonical authority to a
  compatible WaveKit server while preserving `project_uuid`, using authenticated
  preflight, deterministic bundle/blob upload, an authority fence and
  idempotent recovery.
- Added the worker-only, storage-neutral bundle materialization and snapshot
  export boundaries required for WaveKit to host opaque filesystem-backed
  projects without interpreting `.p2p` files.
- Added linked-local clone and attach with a distinct `replica_id`, complete
  bundle/blob verification, resumable staging and atomic publication.
- Added explicit replica status, catch-up, recovery, move, register-copy and
  read-only workflows, with matching read/status behavior through local MCP
  `stdio` where safe.
- Kept credentials in the operating-system keyring and persisted only
  non-secret binding, authority epoch, remote revision and cursor state inside
  the project.
- Kept linked writes disabled and offline reads explicitly stale until the
  subsequent durable-replication protocol is implemented; no optimistic local
  mutation or dual-write path was introduced.
- Preserved workspace schema 4, portable vertical schema 3, canonical bundle
  v1, the `p2p-cli/v1` envelope and the filesystem adapter as the sole
  supported product backend.

## 0.6.1 - 2026-09-01

- Added deterministic project-structure comparison and selective merge from
  one exact portable vertical release or canonical project-memory bundle.
- Added explicit stable-ID placement and collision decisions, dependency
  closure validation, preview tokens bound to source, target, memory and
  authority state, and atomic receipt-backed apply/recovery.
- Added retained canonical structure snapshots and forward-only restore: a
  restore creates the next structure revision instead of rewinding unrelated
  project history.
- Added governed memory dispositions during merge and restore while reusing
  the existing retirement, readiness and classification rules.
- Added the complete privileged CLI lifecycle and read-only MCP comparison and
  retained-snapshot inspection without exposing physical storage paths.
- Preserved workspace schema 4, portable vertical schema 3, the `p2p-cli/v1`
  envelope and the filesystem adapter as the sole supported product backend.

## 0.6.0 - 2026-09-01

- Added immutable `project_uuid` and replica identity distinct from project
  names, paths, storage keys and future remote identifiers, with explicit
  adoption, copy, derivation and collision handling.
- Added the storage-neutral `p2p-canonical-memory/v1` aggregate,
  deterministic `.p2pbundle` import/export and verified `.p2pbackup`
  recovery archives while excluding local credentials and replica state.
- Added a storage-neutral project application boundary with typed repository,
  Unit-of-Work, blob, snapshot, backup/restore, migration and capability ports.
- Retained the optimized filesystem implementation behind a selected adapter
  and reduced `P2PWorkspace` to a compatibility facade used by existing Python
  callers.
- Added the replica-local `.p2p/local/storage.yml` selector, validated legacy
  filesystem fallback, explicit adoption, stable-identity alignment and
  fail-closed mismatch/contradiction handling without dual writes.
- Routed CLI and MCP construction through the same application service while
  preserving the versioned CLI JSON boundary for server consumers.
- Added versioned project-integration manifests and safe lifecycle operations
  for standalone, linked-local and remote-only agent profiles, including
  idempotent refresh/removal and preservation of user-owned files or sections.
- Kept the filesystem adapter as the sole supported product backend; the
  experimental SQLite work remains outside this release and is not required
  to open existing projects.
- Made cross-platform uv qualification current-wheel-only and normalized
  manifest paths across POSIX and Windows without losing ownership evidence.

## 0.5.1 - 2026-08-28

- Made `uv tool install` from the exact GitHub Release wheel the recommended
  local installation path, with uv-managed Python and the tool environment
  outside target projects; retained pip/virtualenv as an explicit fallback.
- Added exact-version `uvx --isolated` guidance, upgrade, rollback, reinstall,
  uninstall, proxy/offline, checksum and attestation documentation without
  making uv a runtime dependency.
- Aligned `p2p doctor`, initialization MCP hints, generated `P2P-SETUP.md`,
  agent policy and Generic, Codex and Claude instructions with platform-aware
  uv-first runtime discovery and explicit owner control of environment changes.
- Added an isolated installed-wheel harness that verifies both CLI and MCP,
  warm/offline cache behavior, project-state byte preservation and the real
  `0.5.0 -> 0.5.1 -> 0.5.0 -> 0.5.1` lifecycle.
- Added Linux x86-64, macOS x86-64, Windows x86-64 and macOS ARM64 uv
  qualification using one immutable candidate wheel. Release source and
  installed-artifact gates use the canonical uv-managed Python 3.12 runtime;
  package metadata continues to permit Python 3.11 and newer.
- Hardened CI workflow validation so runner-scoped temporary paths are bound at
  step execution time and candidate artifact selection is not hard-coded to a
  previous release filename.
- Replaced POSIX-only PID liveness probes with non-signalling Windows process
  handle queries, preventing workspace lock checks from emitting
  `CTRL_C_EVENT` into the caller's console group.
- Closed the exact-retry race where a live competing decision transaction
  could briefly be misclassified as interrupted recovery.

## 0.5.0 - 2026-08-27

- Converged the public P2P Engine 0.5.0 surfaces around workspace schema 4,
  portable vertical schema 3, project-owned structure, memory classification,
  readiness v2, typed AuthorityContext, mutation receipts and registry-v2
  domain discovery.
- Added a release-gate contract inventory and sanitized WaveKit-facing CLI
  fixture bundle that map worker commands, capabilities, AuthorityContext
  behavior, receipts, MCP parity and explicit post-0.5.0 deferrals.
- Kept structure export and replacement as offline, receipt-backed CLI apply
  workflows while MCP exposes only read-only eligibility, inspect and preview
  surfaces.
- Removed executable registry protocol-v1 cache fallback from the current
  runtime; old registry-v1 references remain historical spec/test evidence
  only.
- Removed the Git/synchronization product surface from CLI, MCP, services and
  generated agent guidance. P2P Engine 0.5.0 no longer manages repositories,
  remotes, proposal branches, draft commits, review requests, merges, pushes,
  releases, or branch-based Work lifecycle operations.
- Stopped tracking local implementation-spec history and generated project
  publications, drafts and demo snapshots in the product repository. Demos are
  generated on demand with the current runtime.
- This release is a clean break for current runtime state: P2P Engine 0.5.0
  supports workspace schema 4 and portable vertical schema 3 only. It does not
  provide in-runtime migration, conversion or compatibility aliases for older
  workspace or vertical schemas; recreate or externally convert older
  development workspaces before using this runtime.

## 0.4.11 - 2026-08-19

- Added receipt-backed JSON proposal readiness assessment for WaveKit workers,
  with exact replay, redacted mutation status, atomic readiness/receipt commit,
  rollback and recovery classification.
- Added deterministic readiness source fingerprints and read-only
  `not_assessed`, `current`, and `stale` freshness to proposal detail.
- Routed human CLI and local MCP readiness assessment through the shared atomic
  implementation while preserving advisory governance and owner overrides.
- Updated generated agent guidance and CLI/MCP documentation to distinguish
  proposal assessment, project completeness, UI reads, and worker mutations.

## 0.4.10 - 2026-08-19

- Added the WaveKit-facing CLI JSON contract for project snapshot, project
  initialization, proposal list/show/create/update, proposal contribution
  list/add and redacted mutation status lookup with `--operation-key`.
- Kept MCP stdio protocol-native while aligning proposal and contribution read
  payloads with the CLI read models for standalone agent use.
- Updated generated agent capability guidance to distinguish local MCP agent
  tools from WaveKit's serialized CLI worker retry boundary.

## 0.4.9 - 2026-08-05

- Made workspace transaction lock publication atomic so competing processes
  can observe only an absent or complete lock payload.
- Hardened lock writes against partial operating-system writes and removed the
  lock status check-before-read race during concurrent cleanup.
- Rechecked transient recovery snapshots before classifying proposal decision
  retries as interrupted transactions.

## 0.4.8 - 2026-08-05

- Added `p2p-vertical-transition-impact/v1`, with operation-specific install,
  adoption and migration impact, authoritative empty/populated evidence
  classification, bounded collections and path-free public projections.
- Replaced loose migration mappings with the strict
  `p2p-vertical-transition-plan/v1` workflow: analyze, resolve every exact
  decision, re-preview, then apply with the replacement token.
- Preserved definition, rubric and project-question evidence in their owning
  memory families, with exact mapping or explicit orphan dispositions and no
  fuzzy matching.
- Advanced vertical mutation receipts to schema 2 with semantic
  postconditions, normalized decision summaries and redacted apply/status
  output while retaining internal physical drift detection.
- Made install postconditions describe the installed pack without claiming it
  is active; adoption and migration retain the distinct active-state
  postconditions.
- Updated generated agent guidance, capability inventory and CLI/MCP
  documentation; vertical lifecycle mutation remains owner-governed CLI-only.

## 0.4.7 - 2026-08-04

- Converged the registered CLI, MCP catalog, maintained documentation and
  generated generic, Codex and Claude guidance on one validated public-surface
  and agent-capability catalog.
- Added deterministic template-generation identities and independent content
  drift/template-obsolescence diagnostics for managed agent files.
- Added complete standalone vertical guidance for local catalogs, remote
  registries, device authentication, immutable pull, draft authoring,
  publication and owner-governed project adoption.
- Removed runtime migration/adoption paths and compatibility-only aliases for
  workspace, runtime, proposal artifact, proposal decision, question,
  permission, relation, registry, software-spec, publication, readiness and
  derived-state memory families.
- Made workspace schema 3 and each family-specific current contract the only
  accepted runtime forms. Unsupported state is identified for rejection and is
  never interpreted, normalized or rewritten.
- Removed superseded `.codex/skills/` adapter copies. Fresh Codex integration
  uses the shared current `.agents/skills/` templates.

## 0.4.6 - 2026-08-04

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
  repository. At the time of this release, implementation specifications were
  retained locally under `specs/`; 0.5.0 later stopped tracking that local
  archive.
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
