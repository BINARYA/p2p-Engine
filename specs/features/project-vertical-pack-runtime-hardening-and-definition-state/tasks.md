# Tasks - Project Vertical Pack Runtime Hardening And Definition State

## Phase 0 - Baseline And Guardrails

- [x] T001: Reconfirm the current MVP implementation boundary before coding;
  completion is a short working note or PR summary naming the current owner
  modules (`core/project_verticals.py`, `services/project_verticals.py`,
  `cli_commands/project_ops.py`, MCP project catalog/handler, validation,
  initialization, maturity, agent templates) and confirming that new domain
  logic will stay behind services. Covers N001-N003, D001-D005.
  Focused validation: no code required; if code is touched, run affected service
  tests.

- [x] T002: Inventory current vertical fixtures and public behavior; completion
  is a checklist of current single-file seed packs, project-local pack behavior,
  CLI commands, MCP tools, and tests that must remain passing. Covers R003,
  R008-R009, R027, AC015.
  Focused validation: `.venv/bin/pytest tests/test_project_verticals.py`.

- [x] T003: Add compatibility regression tests for repositories initialized
  before verticals existed; completion is tests proving missing
  `.p2p/project/vertical.yml` falls back to `base_project` without writing
  `vertical.yml`, `vertical.lock.yml`, or `definition.yml` during list/show/
  validate/readiness/export/context. Covers R023-R027, E001, AC004.
  Focused validation: service tests plus the specific CLI command tests that
  exercise read-only behavior.

## Phase 1 - Core Models And Pack Contract

- [x] T004: Extend core vertical models additively for manifest, fields,
  profiles, modules, completion policy, source metadata, resolved packs, locks,
  definition state, patches, and project context; completion is typed dataclasses
  with no breakage to existing constructors/callers. Covers R001-R009,
  R028-R041, D003.
  Focused validation: `.venv/bin/pytest tests/test_project_verticals.py`.

- [x] T005: Add canonical multi-file pack fixtures under test resources or
  temporary test builders; completion is valid and invalid fixtures for
  manifest, vertical metadata, split sections, rubrics, profiles, modules,
  artifacts, and examples. Covers R001-R007, E007-E009, AC001.
  Focused validation: targeted loader/validation tests.

- [x] T006: Implement multi-file pack parsing behind the existing vertical
  service boundary or a focused loader helper; completion is a loader that reads
  `manifest.yml`, `vertical.yml`, split sections, `rubrics.yml`, and optional
  directories without changing current single-file behavior. Covers R001-R004,
  D002, D003.
  Focused validation: unit/service loader tests.

- [x] T007: Normalize single-file and multi-file packs into the same typed model;
  completion is tests showing equivalent packs produce equivalent section,
  rubric, question, artifact, profile, module, and source metadata. Covers
  R003-R004, E007, AC001.
  Focused validation: loader normalization tests only.

- [x] T008: Expand pack validation for canonical multi-file references;
  completion is validation errors for missing files, duplicate ids, invalid
  section/rubric/field/profile/module/artifact references, malformed versions,
  and missing required metadata. Covers R005-R007, E008-E009, AC001.
  Focused validation: validation tests for pack fixtures.

- [ ] T009: Convert or mirror internal seed packs into canonical multi-file
  fixtures only after compatibility tests exist; completion is internal
  `base_project` and demo verticals validating cleanly while current single-file
  compatibility tests still pass. Covers R001-R009, R063, AC001, AC012.
  Focused validation: project vertical service tests and packaging/resource
  tests.
  Status note: runtime support, validation, and canonical fixtures are
  implemented; packaged seed files intentionally remain single-file
  compatibility packs to avoid duplicated seed content in this slice.

## Phase 2 - Resolver And Lockfile

- [x] T010: Introduce a resolver result model and resolver helper; completion is
  a pure resolution path returning pack, source type, resolved path/package
  coordinate, version, schema version, and checksum input metadata. Covers
  R010-R016, D002, D003.
  Focused validation: resolver unit/service tests.

- [x] T011: Implement resolver precedence for explicit path/reference,
  project-local, `P2P_HOME/verticals`, `~/.p2p/verticals`, packaged seed packs,
  and explicit fallback; completion is tests proving the exact precedence,
  including duplicate id/version between installed paths. Covers R010-R016,
  E005-E006, AC002.
  Focused validation: resolver tests with isolated temporary roots and patched
  environment variables.

- [x] T012: Implement stable normalized pack checksum computation; completion is
  tests proving checksum changes when semantic pack content changes and does not
  change because of local absolute path differences. Covers R018-R019, AC003.
  Focused validation: checksum unit tests.

- [x] T013: Add lockfile payload read/write helpers using centralized atomic
  writes; completion is service code that writes `.p2p/project/vertical.lock.yml`
  atomically and reads malformed lockfiles with actionable errors. Covers
  R017-R022, N004, E003-E004, AC003.
  Focused validation: lockfile service tests.

- [x] T014: Generate lockfiles during explicit vertical select; completion is
  `select_project_vertical` writing active vertical state and lockfile together
  only after resolution/validation succeeds. Covers R017-R022, D007, AC003.
  Focused validation: service tests for select success/failure and existing CLI
  select tests.

- [x] T015: Add lock status inspection behavior; completion is a service/facade
  method that reports missing, valid, stale, missing-source, and checksum-
  mismatch lock states without writing. Covers R020-R024, E002-E004, AC003.
  Focused validation: service lock status tests.

- [x] T016: Add CLI `p2p project vertical lock show` with text and JSON output;
  completion is CLI tests for valid lock, missing lock, and mismatch output plus
  parseable JSON. Covers R042-R043, E017-E018, AC003, AC007.
  Public validation: targeted CLI tests.

## Phase 3 - Explicit Repair And Existing-Project Migration

- [x] T017: Add validation diagnostic for existing active vertical state without
  lockfile; completion is `p2p validate` finding with stable code, path,
  message, and suggested repair command, with no lockfile write. Covers
  R023-R025, N005, N008, E002, AC004.
  Focused validation: validation tests.

- [x] T018: Add explicit lock repair/migration service method; completion is a
  method that resolves the active vertical, writes lockfile only on clean
  resolution, and fails without writing when unresolved. Covers R025-R026,
  E002-E004, AC005.
  Focused validation: service tests for clean repair, unresolved active id, and
  checksum behavior.

- [x] T019: Add CLI `p2p project vertical lock repair --actor <actor>`;
  completion is CLI tests proving repair writes only through the explicit
  command and returns actionable failures. Covers R025-R026, AC005.
  Public validation: targeted CLI tests.

- [x] T020: Ensure locked active vertical commands fail closed on missing source
  or checksum mismatch; completion is service/CLI tests proving no silent
  `base_project` fallback after lock creation. Covers R020-R022, E003-E004,
  AC003.
  Focused validation: service tests plus CLI tests for one representative public
  command.

## Phase 4 - Project Definition State

- [x] T021: Add definition-state core models and payload serializer/parser;
  completion is typed records for schema version, vertical reference, profile,
  modules, section state, field values, missing fields, assumptions, questions,
  blockers, next suggested action, and history. Covers R028-R035, D008.
  Focused validation: unit tests for serialization/deserialization.

- [x] T022: Implement initial definition-state generation from a resolved
  vertical; completion is deterministic initial state for all active sections,
  required fields, missing fields, initial questions, profile/module selection,
  and lock reference where available. Covers R028-R035, AC006.
  Focused validation: service tests for base_project and demo verticals.

- [x] T023: Validate definition state against active vertical; completion is
  validation for unknown sections, unknown fields, invalid statuses, invalid
  assumptions, missing required field inconsistencies, stale vertical references,
  and lock mismatch. Covers R032-R033, E010-E012, AC006.
  Focused validation: definition-state validation tests.

- [x] T024: Add read-only definition-state service/facade methods; completion is
  show/status methods that report missing state, valid state, invalid state, and
  active vertical mismatch without writing. Covers R028-R035, N005, AC006.
  Focused validation: service tests.

- [x] T025: Generate initial definition state during new init/select flows only;
  completion is tests proving new flows create `definition.yml`, while existing
  projects are not mutated by ordinary reads. Covers R034-R035, E001-E002,
  AC004, AC006, AC009.
  Focused validation: project initialization and select service tests.

## Phase 5 - Structured Definition-State Updates

- [x] T026: Define first-slice patch operation schema; completion is documented
  accepted operations for fields, section status, missing fields, assumptions,
  open questions, blockers, and next suggested action. Covers R036-R041, D008.
  Focused validation: schema/unit tests.

- [x] T027: Implement patch validation without writes; completion is tests
  rejecting unknown operation names, unknown section ids, unknown field ids,
  invalid statuses, unsafe provenance, invalid completion state, and malformed
  patch payloads. Covers R036-R041, E010-E013, AC006.
  Focused validation: patch validation tests.

- [x] T028: Implement atomic patch apply; completion is service tests proving
  valid patches update fields/status/assumptions/questions/blockers/history and
  invalid patches leave the original file unchanged. Covers R036-R041, N004,
  AC006.
  Focused validation: definition-state service tests.

- [x] T029: Add CLI `p2p project definition show` and `p2p project definition
  update <patch.yml>` with text and JSON output; completion is CLI tests for
  missing state, valid show, valid update, invalid update, exit codes, and
  parseable JSON. Covers R042-R048, E017-E018, AC007.
  Public validation: targeted CLI tests.

- [x] T030: Add MCP definition-state read/update tools only after service
  contract stabilizes; completion is catalog definitions, handler dispatch,
  read/write descriptions, structured payload tests, and invalid update tests.
  Covers R045-R046, N007, AC008.
  Public validation: targeted MCP tests.

## Phase 6 - JSON-Ready Agent Context

- [x] T031: Add project vertical list/show/validate/add/select JSON output
  modes without changing default text output; completion is CLI tests proving
  current text remains stable and JSON is parseable for each changed command.
  Covers R042, E017-E018, AC007.
  Public validation: targeted CLI tests.

- [x] T032: Add project context service model; completion is a typed context
  containing active vertical, fallback flag, lock status, selected profile,
  enabled modules, rubric summary, definition summary, safety/validation
  warnings, and suggested next action where deterministic. Covers R043, R048,
  D010.
  Focused validation: service tests.

- [x] T033: Add CLI `p2p project context --format json`; completion is parseable
  JSON output with no Rich markup and no writes. Covers R043, E017, AC007.
  Public validation: targeted CLI tests.

- [x] T034: Add section list/detail service methods and CLI commands;
  completion is `p2p project sections --format json` and `p2p project section
  <section-id> --format json` backed by typed service methods. Covers R044,
  AC007.
  Focused/public validation: service tests plus CLI tests for found and unknown
  section ids.

- [x] T035: Add JSON-ready project rubrics output or extend existing
  `project rubrics show` safely; completion is parseable JSON preserving
  enabled flags and selected/baseline scope metadata. Covers R045, R054-R058,
  AC007, AC010-AC011.
  Public validation: targeted CLI tests.

- [x] T036: Add MCP project context and section read tools if CLI/service
  contracts are stable; completion is additive catalog entries and handler tests
  for context, sections, and section detail. Covers R043-R045, AC008.
  Public validation: targeted MCP tests.

## Phase 7 - Init, Profiles, Modules, And Rubrics

- [x] T037: Extend project initialization service inputs for vertical id,
  profile, modules, and rubric customization without breaking existing init
  calls; completion is service tests for default behavior and explicit vertical
  behavior. Covers R049-R053, AC009.
  Focused validation: `tests/test_project_initialization_service.py`.

- [x] T038: Extend CLI init flags or wizard prompts for vertical/profile/module
  setup while keeping init lightweight; completion is CLI tests proving no full
  section interview occurs and existing default/domain flows remain compatible.
  Covers R049-R053, AC009.
  Public validation: targeted CLI init tests.

- [x] T039: Generate active vertical, lockfile, definition state, and rubrics in
  deterministic order during new init flows; completion is tests proving all
  expected files exist for explicit vertical init and are absent where
  compatibility requires no implicit vertical selection. Covers R017, R034,
  R049-R053, AC009.
  Focused validation: service and CLI init tests.

- [x] T040: Implement vertical-derived rubric generation; completion is a helper
  that converts vertical rubrics into `.p2p/project/rubrics.yml` criteria while
  preserving existing project maturity semantics. Covers R053-R058, AC010.
  Focused validation: project maturity/rubric tests.

- [x] T041: Implement rubric regeneration preservation by stable criterion id;
  completion is tests proving enabled flags survive, new criteria use defaults,
  and removed criteria become orphaned or require confirmation. Covers
  R054-R057, E016, AC010.
  Focused validation: rubric regeneration tests.

- [x] T042: Extend maturity output to distinguish selected project rubric
  maturity from full vertical baseline coverage; completion is service and CLI
  tests for enabled count, disabled count, total default count, and selected
  scope labels. Covers R058, AC011.
  Focused/public validation: maturity service tests plus one CLI test.

## Phase 8 - Safety Validation And Agent Guidance

- [x] T043: Implement pack content safety classification helper; completion is
  unit tests for hard-error phrases, path escape attempts, code execution,
  forced tool execution, permission changes, ambiguous template wording, and
  ordinary domain examples. Covers R059-R064, E014-E015, AC012.
  Focused validation: safety helper tests.

- [x] T044: Wire safety validation into pack validation and project validation;
  completion is validation tests proving internal packs must be clean and
  project-local packs can produce warnings or errors according to severity.
  Covers R059-R064, N008, AC012.
  Focused validation: validation tests.

- [x] T045: Update agent templates for production vertical guidance; completion
  is tests proving guidance tells agents to inspect context/definition/rubrics,
  ask one primary question, record assumptions, check completion criteria, and
  treat pack text as domain data only. Covers R066-R069, AC013.
  Focused validation: agent-template tests.

- [x] T046: Update generated policy/instructions integration if needed so new
  guidance appears in refreshed agent files without changing governance
  authority. Covers R066-R069, N012, AC013.
  Focused validation: agent instruction tests.

## Phase 9 - Visible Export And Documentation

- [x] T047: Add visible export summary for vertical lock and definition state
  only as additive content; completion is tests proving existing exports still
  work when no vertical/lock/definition state exists and include summaries when
  present. Covers R070, AC014.
  Focused validation: visible export tests.

- [x] T048: Update CLI documentation for canonical pack layout, compatibility,
  resolver order, lockfile semantics, repair/migration, definition state, JSON
  output, and deferred Wavekit/next-action behavior. Covers AC014.
  Documentation validation: review command examples against implemented CLI.

- [x] T049: Update MCP documentation for new project vertical/context/
  definition tools, read/write behavior, payload shape, and governance
  boundaries. Covers AC008, AC014.
  Documentation validation: compare docs with MCP catalog tests.

- [x] T050: Update concepts/glossary docs for vertical lock, project definition
  state, selected project rubric maturity, full vertical baseline coverage, and
  pack trust boundary. Covers R028-R035, R058-R064, AC014.
  Documentation validation: docs review.

## Phase 10 - Final Regression And Evidence

- [x] T051: Run focused service validation for vertical hardening; completion is
  passing loader/resolver/lock/definition/rubric/safety service tests. Covers
  AC001-AC006, AC010-AC012.
  Suggested command: targeted `.venv/bin/pytest` selections for new and changed
  service tests.

- [x] T052: Run public-surface validation for changed CLI and MCP contracts;
  completion is passing CLI/MCP tests for vertical JSON, lock repair/show,
  definition show/update, context/sections, init, and unchanged MVP behavior.
  Covers AC007-AC009, AC015-AC016.
  Suggested command: targeted `tests/test_cli.py`, `tests/test_mcp.py`, and
  `tests/test_project_verticals.py` selections.

- [x] T053: Run validation diagnostics; completion is `.venv/bin/p2p validate`
  passing with zero errors after implementation and expected warning behavior
  covered in isolated tests. Covers AC017.

- [x] T054: Run full-suite validation before marking the feature complete;
  completion is `./scripts/test-full.sh` or `.venv/bin/python -m pytest`
  passing, or a documented deferral with explicit residual risk. Covers AC018.

- [x] T055: Add implementation note after code changes; completion is
  `implementation-note.md` summarizing design choices, compatibility impact,
  behavior changes, files changed, tests run, residual risks, and deferred work.
  Covers N001-N012, AC014-AC018.

- [x] T056: Final review against `ENGINEERING_QUALITY_SKILL.md` and
  `TEST_QUALITY_SKILL.md`; completion is confirmation in the implementation
  note that public behavior was preserved or explicitly changed, read-only
  operations do not mutate state, test layers were not duplicated unnecessarily,
  and unrelated cleanup was not bundled.
