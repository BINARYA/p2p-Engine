# Requirements - Portable Versioned Vertical Packs And Governed Project Adoption

## Origin

- Accepted P2P proposal: `PROP-103`.
- Owner decision: accepted by `mrjungle` on 2026-08-02.
- Product integration: WaveKit owns remote catalogs, authentication,
  authorization, moderation, counters, licenses and artifact distribution.
- P2P Engine owns deterministic local validation, installation, resolution,
  adoption and migration of project verticals.

## Goal

Allow an external system to deliver a declarative, versioned vertical pack to
P2P Engine and then install, adopt or migrate it through deterministic,
machine-readable CLI operations. Existing version-1 and bundled verticals must
remain readable.

## In Scope

- A portable vertical-pack schema version 2.
- Exact coordinates in the form `publisher/vertical-id@semantic-version`.
- Separate structural inheritance and social lineage metadata.
- Deterministic package creation and strict archive inspection.
- Side-by-side installation of exact versions and their dependency closure.
- Project initialization from an explicitly supplied pack and checksum.
- State-bound preview/apply workflows for adoption and migration.
- Preservation of existing project-definition evidence, including explicit
  orphan records when an exact target field does not exist.
- Stable JSON envelopes, error codes and non-zero CLI exit behavior.
- Compatibility tests, operator documentation and release packaging checks.

## Out Of Scope

- A remote registry client in P2P Engine.
- User accounts, catalog visibility, moderation, clone counters or rewards.
- AI-generated vertical content or fuzzy field matching.
- Automatic upgrades, background synchronization or network access.
- Git-based implementation lifecycle behavior.
- Public MCP mutation tools in this delivery. Services must remain reusable by
  a later MCP adapter, but WaveKit integrates through the CLI contract.

## Functional Requirements

### Pack Identity And Schema

- R001: A version-2 pack SHALL declare `schema_version: 2`, `publisher`, `id`,
  and a valid semantic `version`.
- R002: The canonical coordinate SHALL be derived as
  `publisher/id@version`; callers SHALL NOT override it independently.
- R003: Structural composition SHALL use `extends`; social derivation SHALL use
  `lineage.forked_from`; the two concepts SHALL NOT be inferred from each other.
- R004: Every dependency SHALL use an exact coordinate and an expected semantic
  checksum. Version ranges and floating tags SHALL be rejected.
- R005: Version-2 packs SHALL declare a non-empty license identifier.
- R006: Unknown required structure, duplicate identifiers, invalid references,
  inheritance cycles and dependency cycles SHALL produce stable validation
  errors.
- R007: Version-1 and bundled packs SHALL remain readable with their current
  IDs, checksums and precedence behavior.
- R008: Publishing a portable artifact SHALL require schema version 2; a
  version-1 source MAY first be scaffolded or converted explicitly.

### Authoring And Packaging

- R009: `p2p project vertical schema --format json` SHALL expose the supported
  authoring schema and limits without writing project state.
- R010: `scaffold` SHALL create a canonical, declarative pack directory and MAY
  initialize `extends` from one exact installed coordinate.
- R011: `inspect` SHALL support declared and effective views and SHALL perform
  no persistent writes.
- R012: `validate` SHALL accept a canonical directory or portable archive and
  return stable issue codes and paths.
- R013: `package` SHALL produce byte-identical archives for identical semantic
  input, independent of local path and wall-clock time.
- R014: Portable archives SHALL contain only canonical relative paths and
  declarative UTF-8 YAML/JSON/Markdown content.
- R015: Absolute paths, parent traversal, links, executable entries, duplicate
  entries, unsupported file types and excessive entry/file/total sizes SHALL
  be rejected before extraction.
- R016: Artifact checksum SHALL be the SHA-256 of the package bytes; semantic
  checksum SHALL remain the normalized effective-pack checksum.

### Install And Resolution

- R017: Install SHALL use separate `preview` and `apply` operations.
- R018: Preview SHALL validate the artifact, expected checksum, exact
  coordinate, dependencies and conflicts without persistent writes.
- R019: A successful preview SHALL return a state-bound operation token and an
  explicit impact summary.
- R020: Apply SHALL require the preview token, explicit confirmation and actor,
  and SHALL reject stale tokens.
- R021: Apply SHALL commit the target artifact atomically under one
  project-scoped mutation lock only after the complete dependency closure is
  locally present and checksum-verified.
- R022: Exact versions SHALL be installable side by side; an already installed
  identical artifact SHALL be idempotent, while same-coordinate/different-
  checksum input SHALL fail closed.
- R023: Resolution of a portable pack SHALL use its exact coordinate and SHALL
  never silently choose a newer version.
- R024: Lock state SHALL record exact coordinate, semantic checksum, artifact
  checksum and dependency closure additively while retaining legacy parsing.

### Initialization, Adoption And Migration

- R025: Project initialization MAY receive `--vertical-pack` and
  `--expected-checksum`; the pack SHALL be installed before its exact vertical
  is selected.
- R026: Initialization SHALL fail without partial project state when the pack,
  checksum or dependency closure is invalid.
- R027: Adoption SHALL target projects with no meaningful definition evidence
  and SHALL use state-bound preview/apply.
- R028: Migration SHALL target projects with existing definition evidence and
  SHALL use state-bound preview/apply.
- R029: Migration preview SHALL report added/removed/changed sections and
  fields, preserved values, explicit mappings, orphans, blockers and lock
  changes.
- R030: An unchanged section/field identifier SHALL preserve its exact value and
  provenance automatically.
- R031: A moved or renamed field SHALL require an explicit exact mapping; fuzzy
  or similarity-based matching SHALL NOT occur.
- R032: Unmapped source evidence SHALL be retained as explicit orphan state with
  original path, value and provenance; it SHALL NOT be silently discarded.
- R033: Invalid or incomplete mappings SHALL block apply without writing.
- R034: Apply SHALL re-evaluate current state, verify the preview token, acquire
  the project mutation lock and atomically commit vertical state, lock,
  definition state and migration history.
- R035: Concurrent writes to one project SHALL serialize or fail with a stable
  busy error; operations on different projects SHALL not share a global lock.

### CLI Contract And Safety

- R036: New machine-facing commands SHALL support `--format json` and return a
  stable envelope containing `ok`, `operation`, `data`, `warnings` and `error`.
- R037: Errors SHALL expose stable codes for invalid input, unsafe artifact,
  checksum mismatch, dependency failure, conflict, stale preview, confirmation
  required, migration blocked and project busy.
- R038: Read and preview operations SHALL make zero persistent writes.
- R039: A failure before atomic commit SHALL leave all previous project files
  unchanged.
- R040: Text output SHALL remain suitable for operators, while automation SHALL
  rely only on documented JSON fields and exit codes.

## Acceptance Criteria

- AC001: A valid v2 pack can be scaffolded, validated, packaged, inspected and
  installed using only local files.
- AC002: Repackaging unchanged input yields exactly the same archive bytes and
  checksums.
- AC003: Malicious archive path/link/executable/size cases are rejected without
  writes outside or inside project state.
- AC004: Two versions of one coordinate family coexist and exact resolution
  returns the requested version.
- AC005: A stale install/adopt/migrate preview token cannot mutate state.
- AC006: Migration preserves exact matching values and materializes every
  unmatched value as an inspectable orphan.
- AC007: A simulated write failure leaves the old active vertical, lock and
  definition complete and unchanged.
- AC008: Existing v1 project and bundled vertical tests remain passing.
- AC009: CLI contract tests parse every new JSON success and representative
  error envelope.
- AC010: Focused tests, public-contract tests and the full repository suite pass.
