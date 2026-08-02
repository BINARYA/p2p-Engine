# Tasks - Portable Vertical Resolution Convergence 0.4.5

## Task-State Rule

- Source: corrective implementation of accepted `PROP-103` after `0.4.4`
  integration verification.
- Target release: `0.4.5`.
- All implementation tasks are unchecked until direct evidence exists in code,
  tests, documentation or observed release behavior.
- This correction does not authorize remote registry behavior or new MCP
  mutation tools.

## Phase 0 - Regression Baseline

- [x] T001: Add a service regression fixture for a schema-v2 pack whose ID is
  `test-vertical`; completion is a test reproducing the `0.4.4` mismatch between
  a valid exact lock and failed definition/workspace validation. Covers R001-R003,
  R008-R012, E001, AC001-AC002. Focused validation:
  `.venv/bin/pytest tests/test_portable_verticals.py -k hyphen`.
- [x] T002: Add a side-by-side regression with versions `1.0.0` and `2.0.0` of
  one portable ID; completion is tests proving exact coordinate lookup and
  exposing the current lossy bare-ID behavior. Covers R001, R004, E002, AC004.
- [x] T003: Add drift fixtures for active ID/coordinate, lock ID/version/checksum
  and definition version/checksum; completion is focused failing-or-protective
  tests for every incoherent pair before implementation. Covers R010-R011,
  E004-E005, AC005.
- [x] T004: Record the existing v1/bundled resolver precedence tests as the
  compatibility baseline and add any missing duplicate-ID case; completion is
  passing baseline evidence before resolver changes. Covers R006-R007, E006-E007,
  AC006.

## Phase 1 - Exact Reference Resolution

- [x] T005: Replace the lossy reference map with a resolver inventory that
  preserves all distinct exact coordinates and source copies; completion is
  service code that can inspect multiplicity before choosing a pack. Covers
  R001, R004-R006, N003-N004, D002.
- [x] T006: Implement strict coordinate resolution without legacy ID
  normalization; completion is exact lookup tests for hyphens, underscores,
  publisher and version. Covers R001-R002, E001, AC001.
- [x] T007: Implement exact-first bare-ID lookup followed by legacy normalization
  only when exact spelling is absent; completion is tests for `test-vertical`,
  `test_vertical` and legacy space-separated input. Covers R002-R003, R007,
  D001-D003.
- [x] T008: Implement stable ambiguity failure for multiple portable identities
  and portable/legacy collisions; completion is service and CLI tests asserting
  `P2P_VERTICAL_AMBIGUOUS_REFERENCE` and no implicit newest-version choice.
  Covers R004, R022, E002, AC004.
- [x] T009: Implement exact-coordinate conflict detection across sources;
  completion is tests where equal semantic checksums preserve precedence and
  unequal checksums fail with `P2P_VERTICAL_COORDINATE_CONFLICT`. Covers
  R005-R006, E003, AC005.
- [x] T010: Re-run and adjust only the resolver internals needed to preserve
  schema-v1, bundled, user, `P2P_HOME` and project-local precedence; completion
  is the unchanged compatibility matrix passing. Covers R006-R007, AC006.

## Phase 2 - Active State And Definition Convergence

- [x] T011: Harden the authoritative active resolver to cross-check active
  state, exact lock coordinate, lock ID/version/checksum and resolved pack;
  completion is fail-closed diagnostics for every drift fixture and valid
  `0.4.4` state reading without writes. Covers R008-R010, R021, AC005.
- [x] T012: Extend definition validation with exact vertical version and lock
  checksum checks; completion is tests rejecting same-ID/wrong-version and
  wrong-checksum definitions while valid legacy definitions remain compatible.
  Covers R011, E005, AC005-AC006.
- [x] T013: Change sections, definition view, definition patch context, project
  context and `pack_for_definition` to reuse the authoritative active pack;
  completion is focused service tests proving all consumers select the same
  exact version. Covers R012, N004, AC001-AC004.
- [x] T014: Change workspace validation and proposal coverage validation to use
  exact active identity, using the active pack for ID-only coverage tied to the
  current vertical; completion is clean validation for the hyphen fixture and
  explicit ambiguity outside active context. Covers R010-R012, AC001-AC005.
- [x] T015: Change readiness and convergence resolution to preserve
  `active_vertical_coordinate` and validate candidate lock bytes through
  `ProjectReadinessSourceAccess`; completion is filesystem and overlay tests
  proving no bypass of candidate state. Covers R012-R013, AC002-AC005.
- [x] T016: Verify progress, vertical memory, visible export and other callbacks
  that consume definition/sections use the corrected shared services;
  completion is focused regression coverage without duplicate resolver logic.
  Covers R012, N004, AC001-AC003.

## Phase 3 - Lifecycle Candidate Integrity

- [x] T017: Strengthen `validate_migration_candidate` to verify exact active,
  lock, definition, rubrics and questions coherence against the target pack;
  completion is candidate-level tests for every ID/coordinate/version/checksum
  mismatch. Covers R014-R015, R017, D005.
- [x] T018: Prove selection and direct `init --vertical-pack` invoke the complete
  candidate validation before commit; completion is a simulated invalid
  candidate leaving no partial selected state. Covers R014-R018, AC001, AC005.
- [x] T019: Prove adopt preview/apply and migrate preview/apply recompute and
  validate exact target state while preserving token, confirmation, actor,
  locking and rollback semantics; completion is lifecycle tests for success,
  stale preview and injected write failure. Covers R014-R018, AC002-AC003.
- [x] T020: Add immediate post-operation assertions for active, lock,
  definition, sections, readiness and workspace validation after init, adopt
  and migrate; completion is all WaveKit-facing postconditions passing without
  refresh or repair. Covers R016, AC001-AC003.

## Phase 4 - Portable Validation And Public Reads

- [x] T021: Classify schema-v2 canonical directories in the CLI validate path
  and route them through `PortableVerticalPackageService`; completion is
  directory/archive parity tests with unchanged v1 routing. Covers R019, R021-R022,
  D007, AC007.
- [x] T022: Add a derived schema-v2 fixture with exact `extends` and dependency
  checksum; completion is scaffold/inspect/validate/package tests proving exact
  base composition for both directory and archive. Covers R019-R020, E008,
  AC007.
- [x] T023: Add CLI end-to-end tests for hyphenated direct init, install/adopt,
  install/migrate, ambiguous bare reference and representative conflict errors;
  completion is stable JSON fields, error codes and exit statuses reviewed.
  Covers R001-R022, AC001-AC005, AC007.
- [x] T024: Add or update MCP regression tests for existing vertical list/show,
  context, sections and definition reads against an exact active portable pack;
  completion is coherent payloads with no catalog, schema or permission change.
  Covers R012, R022, D008, AC008.
- [x] T025: Add explicit no-write assertions for show, resolve, definition,
  readiness and validate failure paths; completion is unchanged project bytes
  and no newly created state. Covers R017, R021, N001-N002, AC005.

## Phase 5 - Documentation And Release 0.4.5

- [x] T026: Update `docs/CLI-GUIDE.md` to require exact coordinates for
  portable automation, document ambiguity/conflict errors and show a
  hyphenated example; completion is documentation matching tested CLI behavior.
  Covers R001-R007, R022.
- [x] T027: Update version metadata, version consistency tests, `CHANGELOG.md`,
  `docs/INSTALL.md` and CLI primitive inventory from `0.4.4` to `0.4.5` only
  after behavior tests pass; completion is one consistent release version.
  Covers N005, AC009-AC010.
- [x] T028: Add an implementation note for this corrective feature recording
  requirement-to-test evidence, deviations and the unchanged WaveKit/P2P
  boundary; completion is an auditable release summary without unsupported
  completion claims. Covers AC009-AC010.
- [x] T029: Run focused validation:
  `.venv/bin/pytest tests/test_project_verticals.py tests/test_portable_verticals.py`;
  completion is reviewed passing output. Covers AC001-AC007.
- [x] T030: Run public-contract validation with `./scripts/test-public.sh`;
  completion is reviewed CLI/MCP output and no unintended surface changes.
  Covers AC004, AC007-AC009.
- [x] T031: Run `./scripts/test-focused.sh` and `./scripts/test-full.sh`;
  completion is reviewed passing output or an explicit blocker before release.
  Covers AC006, AC009.
- [x] T032: Build wheel and sdist and run
  `scripts/verify-release-artifacts.py --version 0.4.5`; completion is verified
  package contents and matching metadata. Covers N005, AC009-AC010.
- [x] T033: Install the built wheel into an isolated environment and execute the
  hyphenated WaveKit-facing init/adopt/migrate smoke workflow; completion is
  exact coordinates, valid locks/definitions and `p2p validate` success from
  installed artifacts. Covers AC001-AC004, AC010.
- [x] T034: Review the final diff for unrelated refactors, unchecked public
  contract changes and accurate task evidence; completion is a release-ready
  `0.4.5` change whose remaining unchecked tasks are explicitly explained.
  Covers N001-N005, AC009-AC010.
