# Requirements - Portable Vertical Resolution Convergence 0.4.5

## Scope

Restore full conformance of the portable vertical runtime introduced by
`PROP-103`. Version `0.4.4` persists an exact portable coordinate and a valid
lock during init, adoption and migration, but some later reads resolve the
active pack again from the bare vertical ID. That behavior can reject valid IDs
containing hyphens and can select an indeterminate version when multiple
versions are installed side by side.

This feature is a patch-release correction. It does not introduce a new remote
registry boundary or a new vertical lifecycle.

## Origin

- Accepted product direction: `PROP-103`.
- Baseline requirements corrected by this work: R007, R022-R024, R025-R026,
  R034 and R036-R040 from `prop-103-portable-versioned-vertical-packs-and-governed-project-adoption`.
- Earlier locked-definition invariant: R032 from
  `project-vertical-pack-runtime-hardening-and-definition-state`.
- Trigger: WaveKit integration verification against the published `0.4.4`
  wheel found that a valid `publisher/test-vertical@0.1.0` init/adoption can
  leave a valid exact lock while `p2p validate` and
  `p2p project definition show` cannot resolve the active pack.

## In Scope

- Exact-first resolution for portable coordinates and IDs.
- Explicit ambiguity and coordinate-conflict failure behavior.
- Lock-aware active-pack resolution across every active-project consumer.
- Coherence checks for active state, lock, definition and resolved pack.
- Complete pre-commit validation of vertical selection/adoption/migration
  candidates.
- Consistent schema-v2 directory and archive validation.
- Regression coverage for hyphenated IDs and side-by-side versions.
- Patch release metadata, documentation and installed-wheel verification for
  `0.4.5`.

## Out Of Scope

- Network access or remote catalog discovery in P2P Engine.
- WaveKit authentication, visibility, moderation, licensing policy, counters,
  symbolic rewards or artifact download.
- Automatic version selection, floating ranges or background upgrades.
- New public MCP install/adopt/migrate mutation tools.
- A persisted-state schema migration: the exact coordinate and checksums are
  already present additively in schema-v2 active and lock state.
- General refactoring of `ProjectVerticalService` outside exact-resolution and
  active-state correctness.

## Public Surface And MCP Impact

- CLI impact: corrective and backward-compatible. Exact coordinates keep their
  current syntax; ambiguous portable bare IDs fail explicitly instead of
  silently resolving one installed version.
- MCP impact: preserve the existing tool catalog. Existing read tools obtain
  the corrected active pack through shared services; portable lifecycle MCP
  mutations remain deferred under `PROP-103`.
- Storage impact: no schema change and no migration. Existing active state,
  lock and definition files are read more strictly and coherently.
- Agent-facing behavior: corrected read payloads and actionable stable errors;
  no new workflow.
- MCP parity decision: no new mutation parity is required because WaveKit uses
  the documented local CLI artifact boundary. Existing MCP reads require
  regression coverage because they share the affected resolver.

## Functional Requirements

### Reference Resolution

- R001: WHEN a caller supplies a valid exact schema-v2 coordinate, THE SYSTEM
  SHALL resolve only that publisher, vertical ID and semantic version.
- R002: WHEN an exact coordinate includes a hyphenated vertical ID, THE SYSTEM
  SHALL preserve the ID without converting hyphens to underscores.
- R003: WHEN a caller supplies a bare ID, THE SYSTEM SHALL attempt the exact
  trimmed ID before applying legacy space/hyphen normalization.
- R004: IF one bare ID identifies more than one distinct portable coordinate,
  THEN THE SYSTEM SHALL fail with a stable ambiguity error and require an exact
  coordinate.
- R005: IF the same exact coordinate is discovered with different semantic
  checksums, THEN THE SYSTEM SHALL fail closed with a stable coordinate-conflict
  error.
- R006: IF equivalent copies of one exact coordinate have the same semantic
  checksum, THEN THE SYSTEM SHALL preserve documented source precedence without
  changing the selected semantics.
- R007: WHEN resolving schema-v1 or bundled packs by bare ID, THE SYSTEM SHALL
  preserve the existing project-local, `P2P_HOME`, user and bundled precedence
  behavior.

### Active Project Convergence

- R008: WHEN a valid vertical lock contains an exact coordinate, THE SYSTEM
  SHALL use that coordinate as the authoritative active-pack reference.
- R009: WHEN no lock exists for compatible legacy state, THE SYSTEM SHALL use
  `active_vertical_coordinate` when present and bare `active_vertical_id` only
  as the final legacy fallback.
- R010: IF active state, lock and resolved pack disagree on vertical ID,
  coordinate, version or semantic checksum, THEN THE SYSTEM SHALL fail closed
  with an actionable validation diagnostic.
- R011: WHEN definition state is validated, THE SYSTEM SHALL verify its
  vertical ID, vertical version and lock checksum against the authoritative
  active pack and lock.
- R012: WHEN no explicit vertical override is supplied, sections, definition
  reads and writes, project context, readiness, proposal coverage validation,
  convergence, progress, export and workspace validation SHALL use the same
  authoritative active pack.
- R013: WHEN a readiness source overlay supplies candidate active and lock
  bytes, THE SYSTEM SHALL resolve and validate the exact candidate coordinate
  without bypassing the overlay.

### Governed Lifecycle

- R014: BEFORE selection, adoption or migration commits, THE SYSTEM SHALL
  validate the complete candidate set for active state, lock, definition,
  rubrics and project questions when present.
- R015: Candidate validation SHALL verify active coordinate, lock coordinate,
  vertical ID, version, semantic checksum and definition lock checksum against
  the exact target pack.
- R016: AFTER a successful init, adoption or migration, immediate active,
  lock, definition, sections, readiness and workspace-validation reads SHALL
  resolve the same exact pack without repair or registry refresh.
- R017: IF candidate identity validation fails, THEN THE SYSTEM SHALL commit no
  candidate files.
- R018: Existing preview tokens, confirmation requirements, actor attribution,
  project-scoped locking and atomic writer behavior SHALL remain unchanged.

### Portable Validation And Machine Behavior

- R019: WHEN `project vertical validate` receives a canonical schema-v2
  directory, THE SYSTEM SHALL use the same portable validation and inheritance
  composition rules used for a `.p2pv` archive.
- R020: WHEN a schema-v2 pack declares exact `extends`, THE SYSTEM SHALL resolve
  and checksum-validate that exact base rather than treating the coordinate as
  a legacy bare ID.
- R021: Read, inspect, resolve and validate operations SHALL make no persistent
  project writes.
- R022: Existing documented JSON success fields SHALL remain available, and
  corrected failures from machine-facing lifecycle commands SHALL expose stable
  `P2P_...` error codes with non-zero exit status.

## Non-Functional Requirements

- N001: Resolution SHALL remain deterministic and offline.
- N002: The correction SHALL not add a global lock or weaken the existing
  per-project mutation lock.
- N003: Pack discovery SHALL remain bounded by the existing configured pack
  roots and package safety limits.
- N004: The implementation SHALL centralize exact active-pack resolution rather
  than duplicate coordinate fallback logic across consumers.
- N005: The patch SHALL preserve Python and package compatibility declared by
  the repository for the `0.4.x` line.

## Edge Cases And Errors

- E001: `publisher/test-vertical@0.1.0` must not be searched as
  `test_vertical`.
- E002: `publisher/demo@1.0.0` and `publisher/demo@2.0.0` may coexist; `demo`
  is ambiguous while each exact coordinate remains resolvable.
- E003: A manual duplicate exact coordinate with different semantic content is
  a conflict even when source precedence would otherwise select one copy.
- E004: A lock with a valid checksum but an active state naming another
  vertical is invalid.
- E005: A definition with the correct vertical ID but the wrong version or lock
  checksum is invalid.
- E006: Missing active state continues to use the existing read-only
  `base_project` fallback without writing files.
- E007: A legacy active state without a coordinate remains repairable through
  current lock-repair behavior.
- E008: A derived schema-v2 directory with an exact installed `extends`
  coordinate validates and composes successfully.

## Acceptance Criteria

- AC001: A hyphenated schema-v2 pack can complete scaffold, package, install and
  direct init; immediate definition show and workspace validation succeed.
- AC002: Install plus adoption of a hyphenated exact coordinate leaves active
  state, lock and definition coherent and readable.
- AC003: Migration between two exact versions preserves evidence/orphans and
  leaves all active consumers on the target version.
- AC004: Two versions coexist; exact show returns each version and a bare
  ambiguous reference fails with the documented stable error.
- AC005: Active/lock/definition identity drift is detected without writes and
  with actionable diagnostics.
- AC006: Schema-v1, bundled and source-precedence regression tests remain
  passing.
- AC007: Schema-v2 canonical directories and archives, including exact
  inheritance, share valid observable validation behavior.
- AC008: Existing MCP vertical/context/definition reads return coherent data
  without adding mutation tools or changing permissions.
- AC009: Focused service tests, public CLI/MCP tests, full repository tests and
  release artifact verification pass.
- AC010: An isolated environment installed from the built `0.4.5` wheel passes
  the complete WaveKit-facing hyphenated init/adopt/migrate smoke workflow.
