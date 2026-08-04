# Design - Vertical Draft Authoring, Derivation And Publication Lifecycle

## Decision Summary

Drafts and releases are separate objects:

```text
mutable normalized draft
  -> materialized canonical directory
  -> validated deterministic artifact
  -> immutable local release
  -> optional registry publication
```

WaveKit owns user interaction and persistence of its application entities, but
passes a complete normalized document to P2P. It never compiles `manifest.yml`,
`vertical.yml` or `sections/*.yml` itself.

## Normalized Document V1

The document is a typed JSON/YAML object with:

- `contract_version: p2p-vertical-draft/v1`;
- exact target identity (`publisher`, `id`, `version`, `license`);
- title/description metadata;
- distinct `extends`, `lineage.forked_from` and
  `lineage.previous_release` references;
- ordered sections and fields;
- rubrics, profiles, modules and artifact mappings;
- optional source attribution.

Canonicalization sorts map keys and uses stable ordering fields for ordered
collections. The document hash excludes mutable draft metadata such as update
timestamps. Limits are central constants exposed by schema/discovery output.

## Draft Persistence

Drafts live under the user data root:

```text
<data>/p2p-engine/vertical-drafts/<draft-id>/
  draft.yml
  evidence.yml
  artifacts/
```

`draft.yml` contains revision, hash, origin and normalized document.
`evidence.yml` records materialization, validation, package and publication
evidence, each bound to revision/hash. Updates use a per-draft lock and
`AtomicMutationWriter`-equivalent candidate/rename behavior without taking the
project workspace lock.

## Creation

Empty creation emits the minimum document skeleton and an empty `sections`
array. Clone creation uses `VerticalCatalogService` to resolve an exact local
release, calls the effective inspect service, removes release-derived hashes,
sets the requested target identity and records exact origin. The caller must
choose whether the result is a new version, social fork or structural
extension; the service validates the corresponding lineage fields.

## Update And Concurrency

The first delivery accepts complete-document replacement because it is easier
to validate and round-trip from WaveKit than an engine-specific patch language.
`expected_revision` or `expected_hash` is mandatory. A valid update replaces
the document atomically, increments revision and clears all downstream evidence.

## Materialization

`VerticalDraftMaterializer` is the only compiler from normalized document to
canonical files. It writes into a sibling temporary directory, validates the
complete schema-2 pack, then atomically renames into a fresh target. It uses the
same serializer and semantic checksum rules as pack inspection.

Materialization is deterministic:

- manifest and vertical root contain only root-level contract data;
- each section gets one canonical file named from its validated ID;
- optional resources are emitted only when present;
- no wall-clock timestamps enter semantic files.

## Evidence And Publishability

Evidence transitions are monotonic for one revision but invalidated by edits:

```text
drafted -> materialized -> validated -> packaged -> added_local/published
```

Readiness is the proportion of structurally complete governed sections/fields
according to the draft contract; zero sections is explicitly 0. Publishability
requires at least one section, exact identity, license, valid references,
successful materialization/validation and current package checksums.

## Local Add And Remote Publish

`add-local` commits the already verified artifact through the cache writer from
`PROP-105`. `publish` calls its registry publication interface and never
repackages implicitly. Registry receipts are recorded only after the provider
acknowledges the same artifact checksum.

## Proposal Guard

The proposal creation service asks the active vertical for eligible target
sections before allocating an ID or writing files. An empty set raises
`P2P_VERTICAL_NO_TARGET_SECTION`. This is a domain guard shared by CLI and MCP,
not presentation-only validation.

## Module Ownership

- `core/vertical_drafts.py`: normalized document, state and evidence models.
- `services/vertical_drafts.py`: create/inspect/update and lifecycle policy.
- `services/vertical_draft_materializer.py`: canonical file compilation and
  round-trip normalization.
- `services/vertical_packages.py`: reused validation/package behavior.
- `services/vertical_registry.py`: local add/remote publish boundary.
- `cli_commands/verticals.py`: draft command presentation.
- proposal service: no-target-section domain guard.

## MCP Decision

Direct MCP parity is deferred. Draft update is a large persistent write and
needs explicit consent/size policy before exposure through the local MCP
server. WaveKit's server-side worker invokes the CLI and serializes operations.
Service inputs and outputs remain typed and transport-neutral.

## Failure Policy

- No in-place release mutation.
- No stale draft overwrite.
- No caller-authored canonical file layout.
- No package/publication from stale evidence.
- No active or published zero-section release.
- No proposal allocation before target-section validation.

