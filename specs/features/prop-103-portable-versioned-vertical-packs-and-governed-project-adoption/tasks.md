# Tasks - Portable Versioned Vertical Packs And Governed Project Adoption

## Phase 0 - Contract Baseline

- [x] T001: Record accepted `PROP-103`, repository boundaries and the first
  delivery scope in requirements/design/tasks. Covers R001-R040.
- [x] T002: Add compatibility tests for existing v1 packs, bundled packs,
  project-local precedence and current locks before changing resolution. Covers
  R007, R024, AC008.

## Phase 1 - Core Pack V2

- [x] T003: Extend typed pack, manifest and lock models with exact coordinate,
  license, lineage, dependencies and artifact provenance. Covers R001-R005,
  R024.
- [x] T004: Add strict coordinate, SemVer, exact dependency and cycle
  validation while preserving v1 parsing. Covers R001-R008.
- [x] T005: Add recursive project-local discovery and exact-coordinate
  resolution with side-by-side versions. Covers R022-R024, AC004.
- [x] T006: Add `schema`, `scaffold` and declared/effective `inspect` services
  and CLI commands. Covers R009-R011, R036-R040.

## Phase 2 - Portable Artifact

- [x] T007: Implement bounded archive inspection with path, type, link, mode,
  duplicate and size protections. Covers R012, R014-R015, AC003.
- [x] T008: Implement deterministic package generation and artifact checksum.
  Covers R013, R016, AC001-AC002.
- [x] T009: Add directory/archive validation and malicious artifact tests.
  Covers R012-R016, AC001-AC003.

## Phase 3 - Governed Installation And Init

- [x] T010: Reuse the durable project-scoped workspace transaction lock and
  implement the JSON operation/error
  envelope. Covers R035-R040.
- [x] T011: Implement install preview with dependency closure, conflict impact
  and state-bound token. Covers R017-R019, R021-R024.
- [x] T012: Implement confirmed install apply through one atomic candidate and
  prove idempotency/conflict rollback. Covers R020-R024, R034-R035, AC004-AC007.
- [x] T013: Add install CLI preview/apply commands and JSON contract tests.
  Covers R017-R024, R036-R040, AC009.
- [x] T014: Add `p2p init --vertical-pack --expected-checksum` and prove invalid
  artifacts cannot leave a partial initialized project. Covers R025-R026.

## Phase 4 - Adoption And Migration

- [x] T015: Add additive definition-orphan and migration-impact models and
  serialization. Covers R029-R032.
- [x] T016: Implement adoption preview/apply for projects without meaningful
  evidence. Covers R027, R034-R035.
- [x] T017: Implement exact migration mapping, automatic same-ID preservation,
  explicit orphans and blockers. Covers R028-R033, AC006.
- [x] T018: Implement confirmed migration apply with token revalidation,
  project lock, atomic commit and migration history. Covers R034-R035, AC005-
  AC007.
- [x] T019: Add adopt/migrate CLI commands and representative text/JSON
  contract tests. Covers R027-R040, AC009.

## Phase 5 - Compatibility, Documentation And Validation

- [x] T020: Update CLI/API documentation, vertical authoring documentation and
  WaveKit integration examples with the offline artifact boundary. Covers
  R036-R040.
- [x] T021: Verify package resources and installed-wheel behavior for v1 and v2
  packs. Covers R007-R008, AC008.
- [x] T022: Run focused service tests, public CLI/MCP compatibility tests,
  release checks and full test suite; record commands and evidence. Covers
  AC001-AC010.
- [x] T023: Add an implementation note linking completed tasks, deviations and
  deferred MCP mutation parity back to accepted `PROP-103`.
