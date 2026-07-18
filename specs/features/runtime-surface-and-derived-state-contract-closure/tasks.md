# Tasks - Runtime Surface And Derived-State Contract Closure

## Task-State Rule

- Source: local codebase/spec audit after the workspace schema v2 rollout.
- All tasks start unchecked; this feature is a plan, not implementation
  evidence.
- A task may be checked only when its stated code, test or review evidence
  exists.
- Do not modify `.p2p` manually, migrate the workspace, release a package or
  publish Git state while implementing these tasks unless separately requested.

## Stable Delivery Order

```text
P -> S1 -> S2 -> S3 -> S4 -> I -> F
```

- `P`: baseline, traceability and compatibility fixtures.
- `S1`: software-spec compatibility terminology.
- `S2`: canonical bundled vertical seed packs.
- `S3`: per-spec semantic freshness.
- `S4`: complete active Change Set next actions.
- `I`: cross-slice integration and documentation.
- `F`: final validation and residual review.

## Requirement Coverage

| Slice | Requirements |
| --- | --- |
| P | current baseline, N001..014 |
| S1 | R-S1-001..008, E001, AC001 |
| S2 | R-S2-001..014, E002..005, AC002..006 |
| S3 | R-S3-001..025, E006..012, AC007..013 |
| S4 | R-S4-001..012, E013..017, AC014..016 |
| I | public/MCP/storage/docs compatibility, AC017 |
| F | AC018..019 and residual-state decision |

## Implementation Rules

- Follow `specs/skills/ENGINEERING_QUALITY_SKILL.md` and
  `specs/skills/TEST_QUALITY_SKILL.md`.
- Keep domain behavior in services or pure helpers.
- Use existing facades; do not move domain logic into CLI or MCP handlers.
- Preserve established serializers and additive compatibility.
- Test at the lowest useful layer and add public tests only for distinct public
  contracts.
- Never use mtime as semantic identity in S2 or S3.
- Do not create a second seed-pack or software-spec renderer source of truth.
- Record focused command and result evidence in an implementation evidence file
  when implementation starts.
- Maintain the requirement -> design -> task -> test/evidence matrix at every
  slice exit, not only at the final gate.

## P - Baseline And Guardrails

- [x] P-T001: Re-read this feature, the legacy software-spec export feature and
  the vertical-pack hardening feature; completion is a reviewed boundary that
  identifies S1/S2 as closure work and S3/S4 as corrective work.
- [x] P-T002: Capture current `p2p spec --help`, `p2p spec export --help`, MCP
  work-spec catalog descriptions and relevant docs/skills; completion is a
  terminology inventory with every ambiguous phrase mapped to S1.
- [x] P-T003: Capture typed normalized payloads, semantic checksums, list/show
  results and section/rubric order for all four current bundled seed packs;
  completion is test-owned golden baseline data produced through public
  loaders, not copied production duplicates.
- [x] P-T004: Create a pre-conversion bundled-seed lock fixture for at least
  `base_project` and `software_project`; completion is evidence that lock
  validity can be tested after resource conversion without rewriting the lock.
- [x] P-T005: Inventory software-spec renderer inputs and every value consumed
  through `show_change_set`, `show_proposal`, Change Set frontmatter and task
  parsing; completion is an exact source-ownership map for S3.
- [x] P-T006: Capture current generated and imported `provenance.yml` shapes,
  including malformed, missing-source and partial-output examples; completion
  is a legacy classification fixture matrix.
- [x] P-T007: Reproduce the aggregate software-spec mtime false positive with a
  focused failing regression test; completion is one unchanged old spec
  incorrectly staling `software_specs` or downstream state before S3.
- [x] P-T008: Reproduce the missing-second-Change-Set behavior with a focused
  failing regression test; completion is two eligible Change Sets where only
  the first currently appears.
- [x] P-T009: Inventory current generated next-action IDs, ordering, dedupe,
  CLI/MCP limits and refresh counts; completion is a reviewed compatibility
  table naming the intentional S4 behavior change.
- [x] P-T010: Initialize the live requirement -> design -> task -> planned
  test/evidence matrix for all four slices; completion is no unmapped
  requirement or acceptance criterion before implementation starts.
- [x] P-T011: Run focused baseline tests:
  `.venv/bin/pytest -q tests/test_software_spec_service.py
  tests/test_derived_freshness_service.py tests/test_next_actions_service.py
  tests/test_project_verticals.py`; completion is clean evidence or explicitly
  isolated pre-existing failures.
- [x] P-T012: P exit gate. Confirm no unresolved question affects fingerprint
  ownership, legacy origin classification, pack checksum compatibility or
  generated action identity; otherwise update design before S1.

## S1 - Software-Spec Compatibility Terminology

- [x] S1-T001: Define the approved terminology set for native software specs,
  target-specific handoff exports and project-visible export; completion is one
  wording table used by CLI, MCP, docs and skills. Covers R-S1-001..006.
- [x] S1-T002: Correct `p2p spec export` and sibling CLI help where needed;
  completion is unchanged command/argument behavior and help that identifies a
  software-spec downstream handoff. Covers R-S1-001..004.
- [x] S1-T003: Audit and correct MCP work-spec catalog descriptions without
  changing tool names, schemas or permission classes; completion is catalog
  parity with CLI terminology. Covers R-S1-005.
- [x] S1-T004: Update CLI/MCP/glossary documentation to distinguish
  software-spec export from `p2p project export`; completion is factual
  compatibility wording with no unsupported deprecation claim. Covers
  R-S1-002, R-S1-006.
- [x] S1-T005: Update source agent templates and regenerate managed skill copies
  through their existing generation/refresh mechanism only if the inventory
  finds drift; completion is source/generated parity or recorded
  not-applicable evidence. Covers R-S1-007.
- [x] S1-T006: Add focused CLI help and MCP catalog tests using positive
  terminology assertions and the E001 contrast case; completion is passing
  tests that preserve identifiers and schemas. Covers R-S1-008, E001, AC001.
- [x] S1-T007: Run focused S1 validation using the affected CLI, MCP registry
  and docs-hygiene tests; completion is recorded passing evidence.
- [x] S1-T008: Update the live traceability matrix and review diff scope;
  completion is S1 fully mapped with no runtime behavior change.
- [x] S1-T009: S1 exit gate. Check
  `specs/features/legacy-software-spec-export/tasks.md` T005 only when direct
  CLI/docs/MCP/skills/test evidence exists; otherwise leave it open with a
  precise residual note. Covers AC017.

## S2 - Canonical Bundled Vertical Seed Packs

- [x] S2-T001: Add/complete reusable test helpers that load canonical pack
  directories and compare normalized typed models; completion is order-aware
  equality across sections, rubrics, questions, policies, artifacts, profiles,
  modules and examples. Covers R-S2-004, R-S2-010.
- [x] S2-T002: Freeze pre-conversion semantic checksum fixtures for all four
  bundled seeds through the production checksum function; completion is
  path-independent baseline evidence. Covers R-S2-005.
- [x] S2-T003: Add the lock compatibility test using pre-conversion checksum and
  diagnostic path metadata; completion is a failing test if representation
  alone triggers missing-source, mismatch or repair. Covers R-S2-006..008, E004.
- [x] S2-T004: Convert `base_project` to manifest, split sections and rubrics
  with one source per semantic field; completion is normalized equality,
  checksum equality and unchanged fallback behavior. Covers R-S2-001..005,
  R-S2-014.
- [x] S2-T005: Convert `software_project` with the same gates; completion is
  normalized/checksum equality and the unchanged 19-section contract. Covers
  R-S2-001..005, R-S2-014.
- [x] S2-T006: Convert `social_impact_program_design` with the same gates;
  completion is normalized/checksum equality. Covers R-S2-001..005.
- [x] S2-T007: Convert `packaging_or_physical_product_design` with the same
  gates; completion is normalized/checksum equality. Covers R-S2-001..005.
- [x] S2-T008: Add invalid canonical resource tests for missing required files,
  duplicate IDs and aggregate/split duplication; completion is actionable
  validation failures. Covers E002, E003.
- [x] S2-T009: Rerun external single-file, explicit path, project-local,
  `P2P_HOME`, user-home and precedence tests; completion is no compatibility
  drift. Covers R-S2-009, AC005.
- [x] S2-T010: Refactor `scripts/verify-release-artifacts.py` to verify all four
  canonical pack member sets for wheel and sdist; completion is data-driven
  required members with no legacy one-file assumption. Covers R-S2-011..012.
- [x] S2-T011: Add release verifier failure tests that remove one manifest,
  rubrics or section member at a time; completion is deterministic missing-file
  diagnostics. Covers E005.
- [x] S2-T012: Build wheel and sdist in a clean output directory and run release
  artifact verification; completion is proof that all canonical resources are
  packaged. Covers AC006.
- [x] S2-T013: Run an isolated installed-artifact smoke test that lists, shows
  and resolves all bundled seeds without `src/` import leakage; completion is
  passing runtime evidence. Covers R-S2-013.
- [x] S2-T014: Run `tests/test_project_verticals.py` and relevant CLI/MCP
  project-vertical tests; completion is unchanged public semantic payloads
  except the documented diagnostic manifest path.
- [x] S2-T015: Update the live traceability matrix with normalized snapshots,
  checksums, lock and package evidence.
- [x] S2-T016: S2 exit gate. Check the original vertical feature T009 only when
  all four packaged seeds, lock compatibility and built-artifact checks pass;
  replace its old status note with direct evidence. Covers AC017.

## S3 - Per-Spec Semantic Freshness

- [x] S3-T001: Add immutable candidate/source/freshness models with additive
  serialization; completion is compatibility tests proving existing
  `SoftwareSpecStatus.status` remains completeness. Covers R-S3-001,
  R-S3-008..009.
- [x] S3-T002: Extract an exact software-spec source collector from current
  rendering; completion is every consumed value mapped to a canonical relative
  source record with no whole-workspace overreach. Covers R-S3-004, R-S3-021.
- [x] S3-T003: Implement the pure candidate renderer and make refresh consume
  it; completion is identical required-file content and a no-write candidate
  test. Covers R-S3-002..003.
- [x] S3-T004: Define renderer/source-fingerprint contract versions and
  canonical hashing; completion is path/mtime-independent deterministic tests
  and source-order normalization. Covers R-S3-005, N005..006.
- [x] S3-T005: Add the reserved generated provenance block and per-source digest
  manifest; completion is round-trip tests and no loss of existing source
  traceability keys. Covers R-S3-006.
- [x] S3-T006: Add imported-origin provenance normalization with conflict
  handling for engine-owned keys; completion is imported content preservation,
  explicit origin and actionable rejection tests. Covers R-S3-007, R-S3-014,
  E009.
- [x] S3-T007: Implement fingerprinted generated classification for current,
  stale, modified outputs, changed sources and missing required files;
  completion is full candidate-byte comparison, stable reason codes, changed
  path details and suggested commands. Covers R-S3-010..011, R-S3-015,
  R-S3-020, R-S3-023, E010, AC019.
- [x] S3-T008: Implement legacy non-provenance candidate comparison and coherent
  old-provenance recognition; completion is current-legacy, stale-legacy and
  unknown-origin fixture coverage without provenance self-comparison. Covers
  R-S3-012..014, E008..010.
- [x] S3-T009: Handle missing Change Sets/sources, malformed provenance and
  unreadable/partial specs per item; completion is aggregate service continuity
  with explicit diagnostics. Covers E006..009.
- [x] S3-T010: Add coherent source-capture handling for a source that changes
  during the request; completion is a bounded retry or deterministic
  `source_changed_during_read` result with no mixed snapshot. Covers E011.
- [x] S3-T011: Replace only the `software_specs` mtime branch in
  `DerivedFreshnessService` with per-spec aggregate mapping; completion is exact
  state-table tests including no-spec policy. Covers R-S3-016..017, E012.
- [x] S3-T012: Add downstream graph tests proving old-but-current specs do not
  stale visible export/publication and true stale/partial results propagate.
  Covers R-S3-018, AC009..013.
- [x] S3-T013: Add unrelated-source tests proving one proposal or Change Set
  outside a spec's render inputs does not alter its fingerprint. Covers
  R-S3-021.
- [x] S3-T014: Add refresh idempotence tests for candidate bytes, provenance and
  fingerprints. Covers R-S3-022.
- [x] S3-T015: Commit refresh and normalized import candidates through one
  atomic complete-set mutation; completion is failure-injection coverage proving
  no mixed old/new required files. Covers R-S3-024..025.
- [x] S3-T016: Add tree-hash side-effect tests around software-spec statuses,
  project freshness, CLI reads and MCP reads. Covers R-S3-019, AC012.
- [x] S3-T017: Expose additive freshness details consistently through existing
  workspace facade, CLI JSON/text and MCP serialization; completion is public
  compatibility tests with no new tool. Covers R-S3-008, R-S3-020.
- [x] S3-T018: Run focused software-spec, derived-freshness, CLI and MCP tests;
  completion is passing evidence plus review of reason-code stability.
- [x] S3-T019: Update the live traceability matrix and confirm the original mtime
  regression now passes for semantic reasons, not by touching files.
- [x] S3-T020: S3 exit gate. Inspect this repository's existing software-spec
  statuses read-only and record expected legacy/current/unknown classes; do not
  refresh or import artifacts as part of the gate.

## S4 - Complete Active Change Set Next Actions

- [x] S4-T001: Centralize terminal Change Set statuses and define the active
  status priority/rank used by next actions, reusing an existing lifecycle
  source if available; completion is no duplicated contradictory status policy.
  Covers R-S4-001..002, R-S4-006.
- [x] S4-T002: Replace first-match/break behavior with complete eligible registry
  enumeration; completion is one generated action per valid non-terminal Change
  Set. Covers R-S4-001..003.
- [x] S4-T003: Remove decision-context membership from eligibility while
  preserving relation-based proposal enrichment; completion is an active
  registry-only Change Set action with a valid un-enriched reason. Covers
  R-S4-003..004, E014.
- [x] S4-T004: Introduce and document deterministic generated Change Set action
  IDs derived from kind/target; completion is stable IDs across registry order
  and unrelated action insertion. Covers R-S4-005.
- [x] S4-T005: Implement deterministic status-rank/Change-ID ordering while
  preserving the current top-level action-family order. Covers R-S4-006..007.
- [x] S4-T006: Verify curated/generated dedupe precedence for every active
  Change Set, not only the first; completion is one curated action and no
  duplicate generated action for the same `(kind,target)`. Covers R-S4-008,
  E015.
- [x] S4-T007: Apply `limit` only after complete composition and dedupe;
  completion is zero/one/truncated/unlimited service tests. Covers R-S4-009,
  E016.
- [x] S4-T008: Make `refresh.generated` use the same complete generated set and
  keep persistence limited to curated normalization; completion is count and
  tree-content tests. Covers R-S4-011..012.
- [x] S4-T009: Add malformed blank-ID and unknown non-terminal status tests;
  completion is no invalid action, deterministic diagnostics and visible
  unknown valid changes. Covers E017.
- [x] S4-T010: Add zero, one, two and many Change Set service tests with mixed
  terminal states and stable registry reordering. Covers AC014..015.
- [x] S4-T011: Add CLI/MCP parity tests for the complete set and the same `top`
  prefix; completion is unchanged tool schema and matching serialized action
  identities. Covers R-S4-010, AC016.
- [x] S4-T012: Run focused next-action service, CLI and MCP tests; completion is
  passing evidence including the original missing-second-action regression.
- [x] S4-T013: Update the live traceability matrix and review the public identity
  change for generated actions.
- [x] S4-T014: S4 exit gate. Confirm all active Change Sets are visible without
  creating or changing `.p2p/project/next-actions.yml`.

## I - Integration, Documentation And Compatibility

- [x] I-T001: Update architecture/developer documentation for canonical bundled
  resources, exact software-spec source ownership and per-spec freshness;
  completion is documentation matching implementation rather than internal
  call details.
- [x] I-T002: Update CLI/MCP user documentation for additive freshness fields
  and complete next-action behavior, including limit semantics and generated
  action identity. Covers N013.
- [x] I-T003: Run generated agent-template drift checks and regenerate only
  managed outputs whose source templates changed; completion is no unexplained
  generated-file drift.
- [x] I-T004: Run workspace validation and project freshness read-only before
  and after focused tests; completion is no canonical `.p2p` mutation and no new
  false stale chain.
- [x] I-T005: Run the public-contract suite
  `./scripts/test-public.sh -q`; completion is passing CLI/MCP/persistence
  compatibility evidence.
- [x] I-T006: Build distributions and run
  `python scripts/verify-release-artifacts.py --dist <clean-dist>`;
  completion is complete canonical pack contents and correct package metadata.
- [x] I-T007: Review `git diff --check`, generated artifacts and repository
  status; completion is no cache/build pollution or unrelated changes.
- [x] I-T008: Consolidate the requirement -> design -> task -> test/evidence
  matrix while preserving slice-by-slice history; completion is no unmapped
  requirement, edge case or acceptance criterion.

## F - Final Gate And Residual Review

- [x] F-T001: Run the full suite `./scripts/test-full.sh -q`; completion is a
  passing result or a precisely isolated, owner-reviewed residual unrelated to
  this feature.
- [x] F-T002: Re-run the four original observations: ambiguous spec wording,
  single-file bundled seeds, mtime freshness false positive and missing second
  active Change Set; completion is direct evidence that all four are closed.
- [x] F-T003: Verify backward compatibility with external single-file packs,
  pre-conversion vertical locks, legacy software specs and existing
  CLI/MCP identifiers.
- [x] F-T004: Inspect this repository read-only for possible artifact alignment
  after the runtime changes; completion is one of: no alignment needed,
  deterministic refresh recommended per named artifact, curated owner action
  required, or missing primitive. Do not perform alignment in this task.
- [x] F-T005: Confirm no workspace schema change or migration is required by the
  feature and that no `.p2p` file changed during tests except isolated temporary
  fixtures.
- [x] F-T006: Update both original residual feature tasks with direct final
  evidence when complete; leave any unproven task unchecked.
- [x] F-T007: Record package-version/release impact without committing, tagging
  or publishing; completion is an explicit release recommendation and
  compatibility note.
- [x] F-T008: Final review of security, permissions, side effects, deterministic
  hashes, public JSON additions and MCP parity; completion is no unresolved
  high-risk issue.
- [x] F-T009: Produce the implementation handoff summary with changed files,
  focused/full commands, package smoke evidence, residual risks and the F-T004
  artifact-alignment result.
