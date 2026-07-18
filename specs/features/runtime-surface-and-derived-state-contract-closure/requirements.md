# Requirements - Runtime Surface And Derived-State Contract Closure

## Scope

Close four concrete residual implementation gaps found after the workspace
schema v2 rollout:

1. classify the legacy software-spec export consistently as a software-only
   compatibility workflow;
2. convert the four bundled vertical seed packs to the canonical multi-file
   layout already supported by the runtime;
3. replace aggregate software-spec mtime freshness with per-spec semantic
   freshness;
4. expose every active Change Set in generated next actions instead of stopping
   after the first one.

The four slices share a final compatibility and release gate, but they do not
share domain behavior. Each slice must remain independently testable and
revertible.

## Origin

- Local source-code and feature-spec audit performed after the schema v2
  migration.
- Existing residual task:
  `specs/features/legacy-software-spec-export/tasks.md` T005.
- Existing residual task:
  `specs/features/project-vertical-pack-runtime-hardening-and-definition-state/tasks.md`
  T009.
- Observed correction: the `software_specs` freshness node can become stale only
  because one unchanged historical spec has an older mtime than a dependency.
- Observed correction: `NextActionService._fallback_actions()` stops after the
  first non-terminal Change Set and can omit later active Change Sets.

## Current Baseline

- `p2p spec export` still describes its output as a project-definition export in
  one CLI docstring, while the current lifecycle, MCP catalog and most
  documentation describe software-spec handoff artifacts.
- The loader accepts canonical multi-file packs and legacy single-file packs,
  but all four packaged seeds still use one `vertical.yml`.
- Pack checksums are computed from the normalized semantic model. Internal pack
  `resolved_from` already uses a logical package coordinate, while diagnostic
  `path` can identify either `vertical.yml` or `manifest.yml`.
- A vertical lock is valid when the currently resolved normalized checksum
  matches the locked checksum. Representation-only conversion must therefore
  preserve semantic normalization exactly.
- `SoftwareSpecStatus.status` currently reports only `generated` or
  `incomplete`.
- Generated software-spec provenance records source paths but no source
  fingerprint, generator contract version or artifact origin.
- `DerivedFreshnessService` currently compares the newest dependency mtime with
  the oldest required software-spec output.
- `NextActionService` iterates Change Sets, emits one `continue_change` action
  and then breaks.
- `p2p next --top` and MCP `p2p_next(top=...)` already provide the caller-level
  output bound.

## In Scope

- CLI, MCP, documentation and generated-skill terminology for software-spec
  exports.
- Canonical multi-file conversion of `base_project`, `software_project`,
  `social_impact_program_design` and
  `packaging_or_physical_product_design`.
- Release artifact verification for every required bundled pack file.
- A pure deterministic software-spec candidate renderer.
- Versioned source fingerprint and artifact-origin metadata in generated
  software-spec provenance.
- Conservative compatibility classification for legacy generated and imported
  software specs.
- Per-spec freshness details and aggregate freshness derived from those details.
- Complete, deterministic generated next actions for non-terminal Change Sets.
- Existing CLI and MCP read-surface parity.
- Focused, public-contract, packaging and full-suite tests.
- Updating the two original residual task records only after their completion is
  proven by implementation evidence.

## Out Of Scope

- Renaming or removing any `p2p spec` command or MCP tool.
- Replacing the software-spec workflow with the visible project export.
- Removing support for external single-file vertical packs.
- Changing vertical IDs, versions, schema versions, sections, rubrics,
  questions, profiles, modules or completion policies.
- Rewriting project vertical locks merely because packaged file layout changed.
- Automatically refreshing, importing or overwriting historical software specs.
- Treating an unmarked imported spec as generated solely from mtime or path
  conventions.
- Persisting generated next actions as canonical project decisions.
- Changing Change Set lifecycle statuses or owner authority.
- Adding a database, persistent cache or workspace schema v3 migration.
- Releasing a package, publishing Git state or mutating this repository's
  `.p2p` workspace as part of implementation.

## Public Surface And MCP Impact

| Slice | CLI | MCP | Storage | Agent-facing behavior |
| --- | --- | --- | --- | --- |
| S1 software-spec terminology | Help text only; command names and payloads unchanged | Descriptions audited and corrected only where ambiguous | none | Skills and docs use one compatibility classification |
| S2 bundled seed packs | Existing vertical commands preserve semantic results; diagnostic source path may identify `manifest.yml` | Existing project-vertical reads preserve payload semantics | packaged resources change layout; workspace files do not | none beyond documentation |
| S3 semantic spec freshness | Existing status/freshness commands gain additive detail; no write from status | Existing read tools receive the same additive serialized fields | additive keys in generated `provenance.yml`; no migration required | stale guidance becomes per-spec and explainable |
| S4 active Change Set actions | `p2p next` can return more generated actions before `--top` truncation | `p2p_next` has matching behavior | none | all active Change Sets are represented |

MCP parity uses existing tools. No new MCP mutation or consent surface is
required because S1 is terminology, S2 is packaged data, and S3/S4 change
read-only derived results.

## Functional Requirements

### S1 - Software-Spec Compatibility Classification

- R-S1-001: EVERY public description of `p2p spec export` SHALL identify the
  output as a software-spec compatibility or downstream handoff artifact.
- R-S1-002: NO software-spec export help, MCP description, guide or generated
  skill SHALL describe that workflow as the default project-definition export.
- R-S1-003: THE SYSTEM SHALL preserve all existing software-spec command names,
  arguments, target names, exit behavior and serialized payload fields.
- R-S1-004: THE CLI group, subcommand help and success messages SHALL use
  mutually consistent terminology.
- R-S1-005: MCP descriptions SHALL distinguish P2P-native software specs from
  target-specific software-spec exports.
- R-S1-006: Documentation SHALL point project-level visible export needs to
  `p2p project export`, without claiming that software-spec export is deprecated
  or unsupported.
- R-S1-007: Generated project and engine skills SHALL carry the same boundary as
  source templates; generated copies SHALL be refreshed through their normal
  generation path when required.
- R-S1-008: Public help and MCP catalog tests SHALL prevent the misleading
  project-definition wording from returning.

### S2 - Canonical Bundled Vertical Seed Packs

- R-S2-001: EACH bundled vertical seed SHALL use the canonical multi-file
  layout with `manifest.yml`, `vertical.yml`, `sections/*.yml` and
  `rubrics.yml`.
- R-S2-002: OPTIONAL artifacts, profiles, modules and examples SHALL be split
  only when present; empty directories SHALL NOT be required.
- R-S2-003: A bundled seed SHALL have one authoritative representation of each
  semantic field. The conversion SHALL NOT retain duplicated section or rubric
  bodies in both aggregate and split files.
- R-S2-004: FOR each seed, the normalized model before and after conversion
  SHALL be structurally equal.
- R-S2-005: FOR each seed, the normalized semantic checksum before and after
  conversion SHALL be identical.
- R-S2-006: Existing vertical locks for bundled seeds SHALL remain `valid`
  without repair when only the packaged representation changes.
- R-S2-007: The internal logical `resolved_from` coordinate SHALL remain stable.
  The diagnostic source `path` MAY change from `vertical.yml` to `manifest.yml`
  and SHALL NOT be treated as pack identity.
- R-S2-008: New locks created after conversion SHALL resolve the canonical
  manifest while preserving the existing lock schema and package coordinate.
- R-S2-009: External project-local, `P2P_HOME`, user-installed and explicit
  single-file packs SHALL remain loadable with unchanged precedence.
- R-S2-010: All bundled seeds SHALL pass canonical pack validation without
  warnings attributable to the conversion.
- R-S2-011: The build configuration SHALL include every canonical pack file in
  wheels and source distributions.
- R-S2-012: Release artifact verification SHALL check all four seed directories
  and their required canonical files, not one legacy `vertical.yml`.
- R-S2-013: An installed-artifact smoke test SHALL list, show and resolve all
  bundled seeds without relying on the source checkout.
- R-S2-014: `base_project` SHALL remain the default fallback and
  `software_project` SHALL preserve the current 19-section contract.

### S3 - Per-Spec Semantic Freshness

- R-S3-001: Software-spec freshness SHALL be evaluated independently for every
  spec directory.
- R-S3-002: A pure candidate builder SHALL render all required software-spec
  files without creating directories, writing files or changing mtimes.
- R-S3-003: Refresh SHALL write the exact candidate returned by the pure builder
  through the existing owned output boundary.
- R-S3-004: The candidate builder SHALL expose the exact canonical source set
  consumed by rendering, including Change Set inputs and all proposal inputs
  whose values affect output.
- R-S3-005: A versioned source fingerprint SHALL hash source path, source bytes
  or canonical semantic value, render-policy version and generator contract
  version. It SHALL exclude absolute root, source mtime and observation time.
- R-S3-006: Generated `provenance.yml` SHALL record the fingerprint algorithm,
  fingerprint value, generator contract version, artifact origin and the
  per-source digest manifest required to explain freshness. It SHALL also record
  non-provenance output digests when needed to explain output integrity.
- R-S3-007: New imports SHALL be marked as imported using an additive reserved
  provenance block while preserving caller-provided provenance keys.
- R-S3-008: `SoftwareSpecStatus.status` SHALL retain its completeness meaning
  for compatibility. Freshness SHALL be exposed through additive typed fields.
- R-S3-009: The per-spec freshness taxonomy SHALL distinguish at least
  `current`, `current_legacy`, `stale`, `modified`, `unknown_origin` and
  `incomplete`.
- R-S3-010: A fingerprinted generated spec SHALL be `current` only when its
  recorded source fingerprint matches the current source fingerprint, all
  required outputs exist and all required output bytes equal the deterministic
  candidate.
- R-S3-011: A fingerprinted generated spec SHALL be `stale` when its recorded
  source fingerprint differs, with changed source paths reported.
- R-S3-012: A legacy un-fingerprinted spec SHALL be `current_legacy` when its
  non-provenance files equal the deterministic candidate and its legacy
  provenance is internally coherent.
- R-S3-013: A legacy spec with recognizable engine-generated provenance and
  differing candidate content MAY be classified `stale`; ambiguous or imported
  legacy content SHALL be `unknown_origin`, not guessed from age.
- R-S3-014: Imported specs SHALL NOT be marked stale solely because they differ
  from deterministic generated output. Their freshness SHALL be
  `unknown_origin` unless their provenance declares a separately verifiable
  source contract.
- R-S3-015: Missing required files SHALL produce `incomplete` independently of
  fingerprint or origin.
- R-S3-016: The aggregate `software_specs` freshness node SHALL be:
  `current` when every spec is `current`; `current_legacy_fallback` when all are
  current but at least one is `current_legacy`; `stale` when at least one
  generated spec is stale or modified; `partial` when any spec is incomplete or
  has unknown origin; and optional/current according to the existing empty-set
  policy when no specs exist.
- R-S3-017: Aggregate software-spec freshness SHALL NOT compare dependency and
  output mtimes.
- R-S3-018: Downstream freshness nodes SHALL propagate only the semantic
  aggregate state, so an old but semantically current spec does not stale the
  visible export or publication chain.
- R-S3-019: Status, project freshness, CLI and MCP read operations SHALL perform
  zero persistent writes.
- R-S3-020: The status result SHALL include stable reason codes, current and
  recorded fingerprints where applicable, changed source paths and a precise
  suggested command without exposing absolute paths.
- R-S3-021: An unrelated proposal or Change Set change SHALL NOT stale a
  software spec whose render inputs did not change.
- R-S3-022: Refreshing an already current generated spec SHALL be byte
  idempotent except for fields explicitly defined as non-semantic; the preferred
  contract is fully byte-stable output.
- R-S3-023: IF source fingerprints match but one or more generated output files
  differ from the deterministic candidate, THE spec SHALL report `modified`
  with the changed output paths and SHALL NOT silently overwrite them.
- R-S3-024: Refresh SHALL commit the complete required-file candidate atomically;
  a failure before commit SHALL leave the previous complete spec unchanged.
- R-S3-025: Import SHALL validate and normalize provenance before an atomic
  complete-set commit; a failure SHALL NOT leave a mixture of old and imported
  required files.

### S4 - Complete Active Change Set Next Actions

- R-S4-001: Generated fallback actions SHALL include one `continue_change`
  action for every non-terminal Change Set eligible in the current registry
  snapshot.
- R-S4-002: `completed`, `cancelled` and `superseded` Change Sets SHALL not
  generate `continue_change` actions.
- R-S4-003: Change Set lifecycle registry state SHALL determine eligibility.
  Absence from a partial decision-context index SHALL not hide an active Change
  Set.
- R-S4-004: Decision-context relations MAY enrich an action with included
  proposals but SHALL NOT determine whether the action exists.
- R-S4-005: Generated Change Set action IDs SHALL be deterministic functions of
  action kind and Change Set ID and SHALL NOT depend on list position.
- R-S4-006: Generated Change Set action order SHALL be deterministic using an
  explicit lifecycle/priority rank followed by Change Set ID.
- R-S4-007: Existing high-level action ordering SHALL remain: workspace
  alignment, active choice blockers, curated actions, readiness actions and
  fallback actions.
- R-S4-008: Existing deduplication by `(kind, target)` SHALL continue to give an
  earlier curated action precedence over an equivalent generated action.
- R-S4-009: The service SHALL build the complete eligible action set before
  applying the existing caller-provided `limit`.
- R-S4-010: CLI `--top` and MCP `top` SHALL return the same deterministic prefix
  and SHALL make truncation a caller choice, not an internal first-item rule.
- R-S4-011: `next refresh` SHALL report the complete generated action count
  under the same eligibility and deduplication rules as `next`.
- R-S4-012: The correction SHALL introduce no persistent schema change and SHALL
  not turn generated actions into governance decisions.

## Non-Functional Requirements

- N001: Domain decisions SHALL remain in services or pure helpers, not CLI or
  MCP handlers.
- N002: The four slices SHALL not be coupled through a new generic abstraction
  unless concrete duplicate behavior exists.
- N003: Read-only operations SHALL be deterministic and side-effect free.
- N004: Existing compatible persisted artifacts SHALL remain readable.
- N005: New persisted metadata SHALL be additive and versioned.
- N006: Hash inputs and ordering SHALL be canonical and independent of absolute
  checkout path and mtime.
- N007: Errors and diagnostics SHALL use stable machine-readable reason codes
  plus actionable human text.
- N008: Focused tests SHALL cover behavior at service level; CLI/MCP tests SHALL
  cover only their distinct public contracts.
- N009: Packaged-resource tests SHALL inspect built wheel and sdist contents,
  not only source-tree paths.
- N010: No implementation task SHALL edit `.p2p` manually or require repository
  workspace migration.
- N011: The requirement -> design -> task -> test/evidence matrix SHALL be
  initialized before implementation and updated at every slice gate.
- N012: A slice SHALL be mergeable and revertible without requiring unfinished
  code from another slice.
- N013: Public JSON additions SHALL be backward compatible and documented.
- N014: The full public and full test suites SHALL pass before final handoff.

## Edge Cases And Errors

- E001: A help string uses "project definition" only in explanatory contrast
  with `p2p project export`; the negative assertion must not reject that valid
  clarification.
- E002: A canonical pack has a manifest but missing sections or rubrics.
- E003: Split pack files duplicate IDs or contain semantic content different
  from the pre-conversion seed.
- E004: A pre-conversion lock stores a diagnostic path ending in
  `vertical.yml`, while the resolved canonical pack path ends in `manifest.yml`.
- E005: Wheel or sdist includes the manifest but omits split section files.
- E006: A software-spec Change Set no longer exists.
- E007: A spec directory contains only some required files.
- E008: `provenance.yml` is malformed, lacks the reserved block or uses an
  unsupported fingerprint version.
- E009: A legacy imported spec happens to use the same top-level keys as the old
  generator.
- E010: The source fingerprint matches but a required output was manually
  changed.
- E011: A source changes during one status request.
- E012: There are no software specs.
- E013: There are multiple active Change Sets with the same lifecycle status.
- E014: A Change Set is active in the registry but absent from decision context.
- E015: A curated action duplicates one generated Change Set action.
- E016: The caller requests `limit=0`, one item or fewer items than active
  changes.
- E017: Registry data is stale or contains malformed/blank Change Set IDs.

## Acceptance Criteria

- AC001: CLI/MCP/docs/skills tests prove one software-only compatibility
  classification and preserve every command/tool identifier.
- AC002: All four internal seeds use canonical multi-file layout with no
  duplicated section or rubric source.
- AC003: Golden normalization and checksum tests prove each seed is semantically
  unchanged by conversion.
- AC004: A lock created against the pre-conversion semantic checksum remains
  valid after conversion without a repair write.
- AC005: External single-file pack compatibility and resolver precedence tests
  remain passing.
- AC006: Built wheel and sdist verification proves every required canonical seed
  file is shipped.
- AC007: Software-spec candidate rendering is byte-deterministic and write-free.
- AC008: New generated specs record versioned origin and source fingerprint
  metadata.
- AC009: Old semantically current generated specs report
  `current_legacy_fallback` at aggregate level regardless of mtime.
- AC010: A changed source marks only affected recognizable generated specs
  stale and reports the changed source.
- AC011: Imported or ambiguous legacy specs report partial/unknown rather than a
  false generated-stale assertion.
- AC012: Freshness status and aggregate graph inspection leave the workspace
  byte-for-byte unchanged.
- AC013: Downstream nodes remain current when all software specs are
  semantically current.
- AC014: Two or more active Change Sets produce one stable generated action
  each, including an active Change Set absent from decision context.
- AC015: Terminal Change Sets are excluded and curated duplicates retain
  precedence.
- AC016: CLI and MCP limits return the same deterministic prefix, while refresh
  reports the complete generated count.
- AC017: The two original residual tasks are checked only after direct evidence
  for S1 and S2 exists.
- AC018: Focused tests, release-artifact verification, public-contract tests and
  the full suite pass with no repository `.p2p` mutation.
- AC019: A generated spec with unchanged sources but changed output bytes
  reports `modified`, makes the aggregate node stale and is not overwritten by
  a read operation.
