# Tasks - Vertical Draft Authoring, Derivation And Publication Lifecycle

## Phase 0 - Contract

- [x] T001: Bind accepted `PROP-106` to requirements, design and tasks and
  record dependencies/deferred MCP parity. Covers R001-R034.
- [x] T002: Define normalized-document v1, draft/evidence models, limits and
  stable error codes. Covers R001-R005, R010, R015, R019-R022, R033.

## Phase 1 - Draft State

- [x] T003: Implement user-root draft storage, per-draft locking and atomic
  persistence. Covers R004-R005.
- [x] T004: Implement empty and exact-clone creation with explicit lineage and
  no placeholder section. Covers R006-R010, AC001-AC002.
- [x] T005: Implement complete inspect/update with optimistic concurrency and
  evidence invalidation. Covers R011-R015, AC003-AC004.
- [x] T006: Add service tests for deterministic hashes, limits, stale writes,
  concurrent updates and lineage combinations. Covers R001-R015.

## Phase 2 - Materialization And Evidence

- [x] T007: Implement the normalized-document-to-schema-2 materializer with
  fresh-target atomic commit. Covers R016-R018.
- [x] T008: Implement draft readiness, publishability and revision-bound
  validation evidence. Covers R019-R020, AC001, AC004.
- [x] T009: Integrate deterministic packaging and package evidence without
  implicit rematerialization. Covers R021-R022, AC005.
- [x] T010: Add inspect/materialize/inspect round-trip and deterministic-byte
  tests. Covers R016-R022, AC002, AC004-AC005.

## Phase 3 - Catalog And Publication

- [x] T011: Implement immutable local add through the `PROP-105` cache writer.
  Covers R023-R024, AC005.
- [x] T012: Implement remote publish through the registry adapter with exact
  artifact/lineage input and revision-bound receipts. Covers R025-R028, AC006.
- [x] T013: Add publication authorization, immutable conflict, response and
  redaction tests. Covers R023-R028, AC005-AC006.

## Phase 4 - Project Guard And CLI

- [x] T014: Add the no-target-section guard before proposal allocation/write
  and test it through service, CLI and existing MCP entry. Covers R029-R031,
  AC007.
- [x] T015: Add all `p2p vertical draft` commands with text and versioned JSON
  contract tests. Covers R032-R034, AC001-AC007.
- [x] T016: Add WaveKit-oriented golden fixtures for create, inspect, update,
  validation and publication payloads. Covers R002, R011-R014, R019, R027,
  R033.

## Phase 5 - Documentation And Verification

- [x] T017: Document normalized document v1, lifecycle, evidence invalidation,
  lineage and publication. Covers R001-R034.
- [x] T018: Run focused services, CLI/MCP public tests, wheel smoke and full
  suite; record evidence. Covers AC001-AC008.
- [x] T019: Add an implementation note linking evidence and deferred MCP draft
  tools to `PROP-106`.
