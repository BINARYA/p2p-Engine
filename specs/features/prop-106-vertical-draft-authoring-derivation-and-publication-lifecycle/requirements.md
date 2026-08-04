# Requirements - Vertical Draft Authoring, Derivation And Publication Lifecycle

## Origin

- Accepted P2P proposal: `PROP-106`.
- Owner decision: accepted by `mrjungle` on 2026-08-03.
- Depends on schema-2 packs (`PROP-104`), portable artifacts (`PROP-103`) and
  registry services (`PROP-105`).
- WaveKit edits the normalized document; P2P Engine alone materializes
  canonical pack files.

## Goal

Provide one round-trippable authoring lifecycle for creating a vertical from
an empty base or an exact existing release, editing a complete normalized
document, materializing canonical files, validating and packaging a new
immutable release, adding it locally and optionally publishing it remotely.

## In Scope

- Mutable normalized drafts with revision and document hash.
- Empty and exact-clone creation.
- Complete-document inspect and optimistic update.
- Atomic materialization into a fresh canonical directory.
- Readiness and publishability diagnostics.
- Immutable local add and remote publication.
- Separate structural, fork and previous-release lineage.
- Stable no-target-section failure for project proposal mutation.
- CLI/JSON fixtures suitable for WaveKit integration.

## Out Of Scope

- Rich terminal or web editing UI.
- AI generation of vertical content.
- In-place mutation of installed or published releases.
- Registry moderation, clone counters and rewards.
- Initializing a project from an incomplete draft.

## Functional Requirements

### Draft Contract

- R001: A draft SHALL have a stable draft ID, integer revision, normalized
  document, document SHA-256, origin and lifecycle status.
- R002: The normalized document SHALL contain all data needed to materialize a
  schema-2 pack without caller-authored canonical YAML paths.
- R003: Draft serialization SHALL be deterministic; semantically identical
  documents SHALL have the same document hash.
- R004: Draft state SHALL be stored outside project `.p2p` memory under the
  configured user data root or an explicit draft root.
- R005: Draft writes SHALL be atomic and serialized per draft.

### Create And Derive

- R006: `p2p vertical draft create --empty` SHALL create a draft with no
  governed sections, readiness 0 and non-publishable status.
- R007: An empty draft SHALL NOT inject a placeholder `Custom Overview` section
  or field.
- R008: `draft create --from COORDINATE` SHALL resolve one exact local release,
  copy its effective normalized content and record exact parent coordinate and
  semantic checksum.
- R009: A clone SHALL require a new publisher, ID or semantic version before it
  can become publishable.
- R010: `lineage.forked_from`, `lineage.previous_release` and `extends` SHALL
  remain distinct; none SHALL be inferred from another.

### Inspect And Update

- R011: `draft inspect` SHALL return the complete normalized document,
  revision, hash, diagnostics and evidence state without writing.
- R012: `draft update` SHALL accept a complete normalized document and an
  expected revision or hash.
- R013: Updating against a stale revision/hash SHALL fail with
  `P2P_VERTICAL_DRAFT_CONFLICT` and SHALL NOT overwrite newer state.
- R014: A successful update SHALL increment revision, recompute the hash and
  invalidate prior materialization, validation and package evidence.
- R015: Input limits SHALL bound document bytes, section count, field count and
  individual text values before persistence.

### Materialize, Validate And Package

- R016: `draft materialize` SHALL write a complete canonical schema-2 pack to a
  fresh or empty target directory.
- R017: Materialization SHALL be atomic and SHALL reject a non-empty target
  unless an explicit disposable overwrite workflow is used.
- R018: Inspecting a materialized pack SHALL reproduce the draft normalized
  document modulo explicitly documented derived fields.
- R019: Draft validation SHALL report structural validity, readiness percentage,
  publishability and stable issue codes bound to exact revision/hash.
- R020: A draft with zero sections SHALL have readiness 0 and SHALL fail
  publishability with `P2P_VERTICAL_NO_SECTIONS`.
- R021: Package SHALL require current successful materialization and validation
  evidence for the same revision/hash.
- R022: Package output SHALL use the deterministic portable artifact contract
  from `PROP-103` and record artifact and semantic checksums as draft evidence.

### Local Add And Publish

- R023: `draft add-local` SHALL add only a publishable, validated, packaged
  exact release to the immutable user catalog/cache.
- R024: Re-adding identical bytes SHALL be idempotent; same coordinate with
  different checksums SHALL fail closed.
- R025: `draft publish` SHALL submit the exact verified artifact and lineage
  metadata through the registry adapter from `PROP-105`.
- R026: Remote identity, authorization, visibility and moderation failures SHALL
  be returned unchanged as typed registry errors without weakening local
  validation.
- R027: Successful publication SHALL record a remote receipt bound to registry,
  exact coordinate, artifact checksum and draft revision/hash.
- R028: Publication SHALL NOT make an installed release mutable or silently
  advance another project's lock.

### Empty Vertical Project Behavior

- R029: A zero-section vertical release SHALL NOT be installable or selectable
  as an active project vertical.
- R030: If an invalid/recovery workspace has an active zero-section vertical,
  proposal creation SHALL fail with `P2P_VERTICAL_NO_TARGET_SECTION` before
  writing proposal state.
- R031: The no-target-section diagnostic SHALL instruct the caller to complete
  and adopt a valid vertical release.

### CLI Contract

- R032: The CLI SHALL expose `draft create`, `inspect`, `update`, `materialize`,
  `validate`, `package`, `add-local` and `publish` under `p2p vertical`.
- R033: All JSON responses SHALL use the contract from `PROP-107`; normalized
  document and evidence payloads SHALL be versioned independently.
- R034: Read and validation commands SHALL not mutate project state; draft
  mutations SHALL not acquire the unrelated project workspace lock.

## Acceptance Criteria

- AC001: Empty create returns no sections, readiness 0 and no placeholder data.
- AC002: Exact clone, inspect, update, materialize and re-inspect round-trip the
  complete normalized document and correct lineage.
- AC003: A stale update is rejected without changing revision or bytes.
- AC004: Any edit invalidates prior validation/package evidence.
- AC005: A publishable draft produces deterministic bytes and can be added
  locally and pulled/inspected by exact coordinate.
- AC006: Unauthorized remote publication fails without changing local release
  or evidence state except a redacted failed-attempt diagnostic.
- AC007: Zero-section installation and proposal mutation fail before writes
  with their stable error codes.
- AC008: Focused service tests, CLI golden fixtures and full suite pass.

## Public Surface Impact

- CLI: complete `p2p vertical draft` lifecycle.
- MCP: no direct draft mutation tools in 0.4.6; WaveKit invokes CLI using the
  normalized JSON document contract.
- Storage: user-level mutable drafts and immutable release/cache artifacts;
  no draft data in project memory.
- Docs: document schema, lifecycle, lineage and registry publication guide.
- Tests: round-trip, concurrency, evidence invalidation and WaveKit fixtures.

