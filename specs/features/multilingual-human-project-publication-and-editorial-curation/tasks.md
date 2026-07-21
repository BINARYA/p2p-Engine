# Tasks - Multilingual Human Project Publication And Editorial Curation

All tasks are initially unchecked. Mark a task complete only when its code,
tests, documentation, measurement, or recorded evaluation evidence exists.
Planning text is not implementation evidence.

## Implementation Discipline

- Execute slices in dependency order. A later slice may start only after its
  prerequisite exit gate passes.
- Work outside P2P governance for source/spec implementation. Never edit `.p2p`
  manually. The M alignment gate uses supported commands and separate owner
  confirmation.
- Preserve unrelated owner changes in the dirty worktree.
- Keep workspace schema at v3. Publication contract v2 must never be described
  as workspace schema v2.
- Keep deterministic runtime provider-independent and offline-capable.
- Do not add a database, translation provider, language-detection dependency, or
  mandatory PDF dependency.
- Do not infer implementation state from proposal authority, Change Set state,
  Work state, missing evidence, or source-code presence.
- Keep final-reader prose free from P2P workflow and governance mechanics. Do not
  weaken this boundary merely to satisfy current v1 validator tests.
- Use the repository safe YAML loader and atomic write primitives. Do not add ad
  hoc `yaml.safe_load`, direct target writes, or path string manipulation where
  existing structured helpers apply.
- Maintain `traceability.md` after every slice. Do not wait for G to reconstruct
  requirement -> design -> task -> test evidence.
- Record source import provenance, Python executable/version, package version,
  Git revision, fixture identity, and optional PDF capability for every test or
  benchmark result used as acceptance evidence.
- Run focused tests after each task cluster and the required public/full/package
  gates before claiming completion.
- Do not commit, tag, push, publish a release, or regenerate this repository's
  agent/publication outputs as part of implementation slices P..G.

## Delivery Order

| Slice | Depends on | Main result |
| --- | --- | --- |
| P - Preparation | none | baseline, inventory, fixtures, traceability |
| S1 - Edition contracts | P | safe multilingual identity and paths |
| S2 - Evidence and contributions | S1 | complete shared vertical-aware evidence index |
| S3 - Model, packet, and skill | S2 | correct agentic editorial workflow and candidates |
| S4 - Import and freshness | S3 | atomic triplet import and edition provenance |
| S5 - Validation and evaluation | S4 | honest contract validation and editorial evidence |
| S6 - Rendering and review | S5 | language-specific PDF and approval isolation |
| S7 - Public surfaces | S1..S6 | CLI/MCP/facade/docs parity |
| S8 - Compatibility and quality | S7 | legacy, performance, package, and Python gates |
| G - Final implementation gate | S8 | all source behavior and evidence complete |
| M - Repository alignment | G, owner confirmation | generated local artifacts refreshed |

## P - Preparation And Baseline

- [x] P-T001: Re-read `requirements.md`, `design.md`, `traceability.md`, the
  complete `prop-099-human-project-publication-pipeline` feature, and the current
  publication/agent source and tests. Record any source behavior that invalidates
  this design before editing runtime code. Covers AC023.
- [x] P-T002: Create `implementation.md` in this feature directory with sections
  for environment/import provenance, current baseline, per-slice evidence,
  public behavior, editorial evaluations, performance, compatibility, package
  verification, residual risks, and M alignment. Covers N012..N014, AC020..024.
- [x] P-T003: Update `traceability.md` from planned to active and verify every
  A/B/C/D/E/F/G/N/X/AC item has an owning design decision, task, and planned test
  or evaluation. Add missing rows before implementation. Covers AC023.
- [x] P-T004: Inventory the existing v1 publication artifact paths, manifest
  schema, fingerprint inputs, stage invalidation, facade methods, CLI commands,
  MCP tools, generated adapter files, release-template IDs, and tests. Record a
  behavior table and exact compatibility decisions in `implementation.md`.
  Covers G-R011..G-R017, X023..X024.
- [x] P-T005: Capture current source-tree publication test results and focused
  CLI/MCP/agent test results with import provenance. Record current failures,
  skips, optional WeasyPrint state, and total runtime. Covers N012..N013, AC020.
- [x] P-T006: Capture a baseline publication prepare/status profile and operation
  counts on current 100, 1,000, and 10,000 proposal fixtures. Include source
  reads, YAML parses, lifecycle evaluations, vertical loads, exported bytes,
  packet bytes, and wall time. Covers E-R011, N007, AC021.
- [x] P-T007: Add or extend isolated fixture builders for software, board-game,
  custom/no-valid-vertical, multilingual, active-unmapped, historical/revoked,
  contradictory, duplicated, process-only, attributed/unattributed contribution,
  and unrelated-brand contamination cases. Covers B-R002..B-R008,
  F-R009..F-R010.
- [x] P-T008: Snapshot representative current v1 output files and manifest
  payloads as compatibility fixtures without copying live derived outputs into
  canonical test data. Covers G-R014..G-R016, X023.
- [x] P-T009: Define focused commands for S1..S8 plus CLI, MCP, agent lifecycle,
  PDF optional/installed, performance, Python 3.11, current Python, public, full,
  wheel, and sdist suites in `implementation.md`. Covers N012..N014, AC020.
- [x] P-T010: Preparation exit gate. Confirm the feature corrects publication
  behavior only, keeps workspace schema v3, retains one project scope across
  language editions, and leaves live repository alignment to M.

## S1 - Edition Identity, Language, Profile, And Paths

- [x] S1-T001: Add immutable core contracts for `PublicationEdition`, normalized
  language, output-name validation result, edition paths, edition catalog entry,
  and edition diagnostic. Include exact JSON-ready serializers. Covers A-R001..
  A-R009, N011.
- [x] S1-T002: Implement language normalization with whitespace trimming,
  `_`/`-` handling, BCP 47 casing, lowercase path tag, aliases `eng -> en` and
  `ita -> it`, and stable diagnostic codes. Cover empty, malformed, extension,
  separator, script, region, variant, equivalent alias, and future valid primary
  language cases. Covers A-R001..A-R003, X001..X002.
- [x] S1-T003: Implement output-name validation with the exact ASCII slug and
  64-character contract. Reject traversal, hidden/reserved names, extensions,
  separators, controls, empty names, and normalization collisions before any
  directory is created. Covers A-R004..A-R006, X003, N005.
- [x] S1-T004: Implement one `PublicationEditionPathResolver` for shared,
  per-edition, candidate, final Markdown/PDF, and default-English alias paths.
  Assert every resolved target remains under its declared root after symlink-
  aware resolution. Covers A-R005..A-R008, N005, X011.
- [x] S1-T005: Define strict v2 profile and catalog codecs with duplicate-key
  detection, explicit supported/future-version diagnostics, deterministic
  ordering, and atomic writes. Covers A-R009..A-R010, G-R013, N002..N003,
  X014.
- [x] S1-T006: Replace fixed profile values `project_default`, `mixed`, and
  generic appendix configuration with edition identity, no-P2P-reader contract,
  vertical-adaptive structure, body-traceability false, contribution policy, and
  neutral theme. Covers A-R001..A-R010, D-R001, G-R013.
- [x] S1-T007: Refactor publication path/status/result dataclasses to carry
  edition identity and use path resolver outputs. Preserve stable default calls
  by resolving omitted fields to `(project, en)`. Covers A-R007..A-R010,
  G-R011, N011.
- [x] S1-T008: Implement edition catalog discovery from committed per-edition
  manifests. Sort by output name then canonical language, reject key/manifest
  mismatches, and never rebuild publication evidence during catalog reads.
  Covers A-R009, E-R010, N003..N004.
- [x] S1-T009: Add collision and execution-order tests proving English/Italian,
  `eng`/`en`, regional tags, and custom output names cannot overwrite each
  other. Cover prepare-order symmetry without yet requiring later-stage files.
  Covers A-R003..A-R008, X002..X005, AC001..AC002.
- [x] S1-T010: Add path-safety tests for traversal, symlinks, hidden/reserved
  names, canonical target as input, and Windows-style separators on POSIX.
  Covers N005, X001..X003, X011.
- [x] S1-T011: Update traceability with actual contracts, paths, diagnostics, and
  focused test IDs. Run focused core/profile/path/catalog tests on Python 3.11
  and current Python.
- [x] S1-T012: S1 exit gate. The default edition is `project-en`; every edition
  has non-colliding exact paths; no source/evidence/editorial behavior has been
  inferred from language identity.

## S2 - Shared Vertical-Aware Evidence And Contributions

- [x] S2-T001: Add immutable v2 contracts for evidence source, evidence entry,
  vertical metadata, classification, contribution row/summary, evidence index,
  and generation diagnostic. Include strict invariants and JSON/YAML-ready
  serializers. Covers B-R001..B-R008, D-R002..D-R007, N011.
- [x] S2-T002: Define the exact publication evidence source catalog and document
  why each provider/source class is included or excluded. Include project
  definition, vertical pack/memory, active unmapped evidence, historical state,
  risks, assumptions, questions, contributions, and process-only records.
  Covers B-R002..B-R007, E-R012.
- [x] S2-T003: Implement `ProjectPublicationEvidenceService` over one
  `WorkspaceReadContext`. Reuse registry bundle, lifecycle batch, active vertical
  state, vertical memory, and project snapshots once per generation. Covers
  B-R001..B-R003, E-R011, N007.
- [x] S2-T004: Implement stable evidence IDs from evidence kind, canonical source
  path/selector, and semantic content identity. Prove IDs and order are invariant
  under reversed directory/provider enumeration and process restart. Require a
  complete normalized payload or a hash-bound complete source locator for every
  entry; reject snippet-only evidence. Covers B-R003, N003, N008.
- [x] S2-T005: Implement deterministic authority/editorial classification for
  active section evidence, active cross-cutting/unmapped evidence, historical
  context, unresolved contradictions, duplicates, insufficient evidence, and
  process-only records. Covers B-R004..B-R007, X006..X010.
- [x] S2-T006: Integrate required/applicable vertical sections and generate
  stable reader-question seeds without turning section IDs into mandatory final
  headings. Preserve explicit generic fallback when vertical state is absent or
  invalid. Covers B-R010..B-R018, X006.
- [x] S2-T007: Preserve every active unmapped evidence item in a dedicated
  cross-cutting group and expose total/mapped/unmapped/historical/process-only
  counts. No first-N limit or implicit truncation is allowed. Covers B-R005,
  B-R008, X007, AC004.
- [x] S2-T008: Keep the complete visible export as a path/hash source. Remove
  full export bytes from the packet input model and add a test that packet size
  does not scale linearly with `project.md` byte size. Covers B-R009..B-R010,
  AC003.
- [x] S2-T009: Implement contribution-record selection from current authoritative
  project evidence. Exclude historical/process-only records and retain
  unattributed records. Record exact selected source IDs for audit. Covers
  D-R002, D-R004, D-R007.
- [x] S2-T010: Implement NFC/whitespace author normalization without guessed
  alias/case merging. Emit identity-quality advisories for suspicious variants.
  Covers D-R003, X016.
- [x] S2-T011: Implement deterministic largest-remainder basis-point allocation,
  tie ordering, percentage formatting, denominator, and limitation statement.
  Cover zero, one, equal, repeating decimal, large counts, unattributed, and
  reversed-order cases. Covers D-R004..D-R007, X017, AC011.
- [x] S2-T012: Implement `auto|include|omit` contribution policy during profile/
  evidence preparation. Cover no attributed data, all unattributed, one author,
  multiple authors, include failure, and omit behavior. Covers D-R001,
  D-R008..D-R010, X015.
- [x] S2-T013: Write `publication-evidence.yml` atomically only after strict
  self-validation. Reuse it when source fingerprint, generator version, vertical
  identity, and source-export hash are current and its own hash matches. Covers
  B-R001, E-R007..E-R009, N002.
- [x] S2-T014: Add golden/parity tests for software, board-game, custom vertical,
  invalid vertical, active unmapped, revoked, superseded, contradictory,
  duplicate, process-only, and contribution fixtures. Covers B-R002..B-R018,
  X006..X010.
- [x] S2-T015: Add structural scale tests at 100, 1,000, and 10,000 proposals.
  Assert one lifecycle batch, one vertical load, bounded YAML reads/parses, no
  proposal-count-squared work, deterministic bytes, and explicit total counts.
  Covers B-R008, E-R011, N007..N008, AC021.
- [x] S2-T016: Compare the index against the exact source catalog and fail tests
  if a selected source class is silently absent or a process-only class is
  promoted to project evidence. Include a losslessness audit proving every
  inline payload or source locator reconstructs the full selected evidence unit.
  Covers B-R002..B-R007, E-R012.
- [x] S2-T017: Update traceability and implementation evidence with source
  catalog, operation counts, index sizes, contribution examples, and residual
  classifications.
- [x] S2-T018: S2 exit gate. All evidence is indexed or explicitly classified,
  no fixed-count truncation exists, contributions are deterministic and honest,
  and prepare does not rescan the workspace per edition.

## S3 - Publication Model, Curator Packet, And Skill

- [x] S3-T001: Add strict v2 codecs/contracts for project model, reader question,
  claim, adaptive outline, vertical coverage disposition, editorial assessment,
  evidence accounting, and binding metadata. Reject duplicate IDs and invalid
  enums at parse time. Covers B-R011..B-R017, C-R004, C-R018, E-R003.
- [x] S3-T002: Implement referential validation for reader-question -> claim,
  outline -> claim, claim -> evidence, vertical-section -> outline, and evidence
  accounting -> claim links. Covers B-R012..B-R017, E-R004, X009..X010.
- [x] S3-T003: Implement exact-set evidence accounting validation. Require one
  disposition for every index entry, used-to-claim links, reasons for exclusions,
  and correct treatment of process-only/historical evidence. Covers B-R013..
  B-R015, E-R004, X008..X010, AC005.
- [x] S3-T004: Replace `_curator_input_text` with a bounded v2 packet that records
  edition/profile/vertical/source/evidence hashes, project reader contract,
  contribution policy, allowed knowledge boundary, exact candidate triplet, and
  corrective commands. Do not embed full `project.md`. Covers B-R009..B-R010,
  C-R001..C-R003, C-R017, AC003.
- [x] S3-T005: Bind packet freshness to source fingerprint, source export,
  evidence index, profile, edition identity, and packet contract version. Cover
  changed index bytes with unchanged path and changed profile language/policy.
  Covers B-R015, E-R003, E-R006..E-R009.
- [x] S3-T006: Rewrite the release-template `p2p-project-curator/SKILL.md` as a
  concise execution guide: verify, inspect vertical, traverse evidence, build
  model, account evidence, write prose, self-assess, emit candidates, stop.
  Covers C-R001..C-R018.
- [x] S3-T007: Add generated one-level skill references for editorial workflow,
  model/evidence schemas, vertical interpretation, and editorial rubric. Remove
  duplicated detail from `SKILL.md` and keep references directly discoverable.
  Covers C-R015..C-R016.
- [x] S3-T008: Remove instructions requiring visible proposal/decision/Change/
  Work IDs, `.p2p` source-of-truth boilerplate, workflow-state chapters, fixed
  `Executive Summary` wording, or direct canonical output writes. Covers
  C-R005..C-R014, C-R017, F-R003.
- [x] S3-T009: Add explicit prohibitions against implicit adjacent-project
  knowledge, invented implementation state, audience variants, and curator-
  calculated contribution percentages. Covers C-R002, C-R012, D-R007,
  F-R010, AC012.
- [x] S3-T010: Update all agent template manifests/registrations so install,
  update, doctor, uninstall, drift detection, and adapter coexistence own the
  entire skill resource set. Preserve unrelated installed adapters. Covers
  C-R016, G-R017, X024, AC017.
- [x] S3-T011: Update embedded non-skill adapter guidance to carry the same core
  boundary and point to packet-declared contracts without duplicating the full
  reference set. Covers C-R015..C-R017, G-R017.
- [x] S3-T012: Run the system skill validator or equivalent release-template
  validation against materialized `.agents` and `.codex` skills. Verify valid
  frontmatter, concise length, direct reference links, no deep reference nesting,
  and no stale v1 output paths. Covers C-R015..C-R016, AC017.
- [x] S3-T013: Add skill behavior tests using raw isolated packets for software,
  board-game, custom vertical, and contamination-trap fixtures. Do not include
  the expected prose in the evaluator prompt. Covers F-R009..F-R010.
- [x] S3-T014: Add static template tests proving no WaveKit or unrelated brand
  name, hard-coded software-only outline, or proposal-dump instruction exists in
  release/generated resources. Covers C-R002, C-R007, F-R010.
- [x] S3-T015: Verify candidate triplet paths from packet, edition resolver, CLI
  help examples, and skill references are byte-identical strings. Covers
  C-R017, E-R002, N010.
- [x] S3-T016: Update traceability and record generated resource lists, template
  IDs/versions, packet size before/after, and skill validation evidence.
- [x] S3-T017: S3 exit gate. The skill produces model/accounting/prose candidates
  for the final reader, uses the active vertical, accounts for all evidence, and
  cannot be steered by the old proposal-export outline.

## S4 - Atomic Import, Manifest, Catalog, And Freshness

- [x] S4-T001: Refactor `ProjectPublicationService.import_curated` into an
  edition-scoped triplet import receiving Markdown, model, and evidence-
  accounting sources plus validated edition identity. Keep a compatibility
  wrapper only where the public contract requires it. Covers E-R001..E-R004,
  G-R011.
- [x] S4-T002: Extend safe source resolution to all three candidates. Enforce
  repository-local, non-`.p2p`, non-canonical, regular UTF-8/YAML file,
  extension, symlink, and distinct-path rules. Covers E-R002..E-R003, N005,
  X011.
- [x] S4-T003: Validate current packet/profile/source/evidence hashes and exact
  edition identity before reading candidate semantics. Return stable stage-
  specific diagnostics and corrective prepare command. Covers E-R003, E-R006,
  N010.
- [x] S4-T004: Parse model/accounting with the strict v2 codecs and run all
  identity, version, evidence-set, claim, outline, vertical-coverage, and
  contribution-policy checks before staging outputs. Covers E-R003..E-R004,
  F-R001, X009..X010, X014..X015.
- [x] S4-T005: Implement a focused import transaction that captures prior
  manifest revision, stages all files under the target filesystem, atomically
  replaces model/accounting/Markdown, and atomically commits manifest last.
  Covers E-R005..E-R006, N002.
- [x] S4-T006: Add failure injection before/after every staged replace and
  manifest commit. Prove cleanup, preservation of prior current revision, and
  explicit incomplete status without mixed-ready state. Covers E-R005,
  E-R010, X012.
- [x] S4-T007: Define per-edition manifest v2 stage payloads and hash bindings
  for profile, packet, model, accounting, Markdown, validation, render, review,
  and aliases. Add strict future/invalid-version behavior. Covers E-R006,
  G-R013..G-R015, X014.
- [x] S4-T008: Refresh the shared edition catalog from committed manifests only,
  with atomic write, stable sorting, stale-entry diagnostics, and no source
  rebuild on read. Covers A-R009, E-R005..E-R010, N003..N004.
- [x] S4-T009: Implement stage-status evaluation and invalidation so shared drift
  affects all editions while local profile/model/accounting/Markdown drift
  affects only one edition's descendants. Covers A-R008, E-R007..E-R010,
  X004..X005, X013.
- [x] S4-T010: Detect manual modifications by content hash for every imported or
  generated edition file. Reads must report drift and never repair it. Covers
  E-R008, N004, X013.
- [x] S4-T011: Make byte-equivalent prepare/import idempotent. Record whether
  files were reused/written and do not invalidate later stages when semantic and
  physical hashes remain current. Covers E-R009, N010.
- [x] S4-T012: Add concurrent import tests for two different editions and two
  competing revisions of one edition. Different editions may proceed safely;
  stale same-edition revision must fail rather than overwrite a newer commit.
  Covers A-R006..A-R008, E-R005..E-R010.
- [x] S4-T013: Add end-to-end import tests for complete, 99%-accounted, unknown
  ID, duplicate disposition, claim-without-evidence, used-without-claim, wrong
  language, stale packet, stale index, unsafe path, and unsupported version.
  Covers E-R001..E-R010, X009..X014, AC005.
- [x] S4-T014: Update traceability and implementation evidence with transaction
  sequence, failure matrix, manifest schema, freshness graph, and cross-edition
  isolation results.
- [x] S4-T015: S4 exit gate. A committed edition revision always consists of a
  mutually bound model, complete accounting, and Markdown; status cannot report
  partial mixed files as current.

## S5 - Validation And Editorial Forward Evaluation

- [x] S5-T001: Refactor validator inputs/results to carry edition identity,
  shared evidence, model/accounting paths/hashes, contract versions, and stable
  finding locations across Markdown and YAML. Covers F-R001, F-R005, N011.
- [x] S5-T002: Implement deterministic chain validation for edition paths,
  profile/packet/manifest/source/evidence/model/accounting/Markdown hashes and
  supported versions. Reuse strict contract validators rather than duplicating
  parsing rules. Covers F-R001, E-R006..E-R008.
- [x] S5-T003: Replace exact `Executive Summary` and visible `.p2p` authority
  requirements with language-neutral structural checks and model role coverage.
  Cover English, Italian, regional language tags, and unknown valid tags. Covers
  F-R002..F-R003, X018, AC010.
- [x] S5-T004: Add deterministic Markdown errors for empty document, UTF-8,
  exactly one H1, unclosed fences, unsafe target, and internal proposal,
  decision, Change Set, or Work IDs in normal reader prose. Define treatment of
  code fences and legitimate P2P Engine product terms explicitly. Add a fixture
  proving generic proposal/decision/lifecycle concepts are allowed as evidenced
  product subject matter while IDs and upstream status dumps are not. Covers
  F-R002, X019..X020.
- [x] S5-T005: Add heuristic findings for probable language mismatch, weak
  vertical framing, governance/workflow narration, proposal chronology,
  readiness percentages, placeholders, chapter imbalance, contribution wording,
  and model/prose claim mismatch. Document false-positive limitations. Covers
  F-R004..F-R007.
- [x] S5-T006: Verify warnings/advisories never block render and deterministic
  errors always do. Preserve stable text/JSON/YAML finding codes and line/path
  locations. Covers F-R005..F-R007.
- [x] S5-T007: Implement contribution chapter validation against the prepared
  summary and profile policy. Detect missing limitation, incorrect totals,
  recalculated figures, forbidden effort/ownership claims, unexpected chapter,
  and missing required chapter. Covers D-R007..D-R010, F-R001, X015..X017.
- [x] S5-T008: Materialize the versioned editorial rubric reference and an
  evaluation record schema separating self-assessment, independent evaluator,
  and owner review. Covers C-R018, F-R008.
- [x] S5-T009: Define rubric thresholds before running evaluations. Require no
  unsupported external facts/internal workflow narration and minimum recorded
  scores for autonomy, vertical coherence, evidence use, language consistency,
  structure, and reader usefulness. Covers F-R008..F-R010, AC008.
- [x] S5-T010: Run blind forward evaluation on the software fixture. Verify
  active unmapped and historical evidence dispositions, adaptive software
  explanation, no implementation inference, and no proposal dump. Covers
  B-R005..B-R017, C-R005..C-R014, F-R009.
- [x] S5-T011: Run blind forward evaluation on the board-game fixture. Verify the
  resulting structure prioritizes gameplay concepts such as players, setup,
  components, rules, progression, and completion as supported, without a
  software outline. Covers C-R007..C-R008, F-R009.
- [x] S5-T012: Run blind forward evaluation on custom/no-valid-vertical and
  contamination-trap fixtures. Verify explicit generic framing and zero
  unsupported adjacent-project/brand claims. Covers B-R018, C-R002,
  F-R009..F-R010, AC007..AC008.
- [x] S5-T013: Run at least English and Italian editions over equivalent project
  evidence. Evaluate project-scope invariance, language consistency, localized
  natural headings, and independent model hashes. Covers A-R010, C-R006,
  F-R009, AC009.
- [x] S5-T014: Apply citation-erasure/autonomy review to each forward-evaluation
  document and record whether it remains understandable without sidecars or
  internal references. Covers C-R010, C-R014, AC006.
- [x] S5-T015: Feed all forward-evaluation defects back into the skill,
  references, packet, contracts, or heuristics; rerun affected fixtures until
  thresholds pass. Do not weaken deterministic contracts to pass a prose sample.
- [x] S5-T016: Update traceability with validator code/test evidence, evaluation
  inputs, rubric results, known heuristic limits, and corrected defects.
- [x] S5-T017: S5 exit gate. Deterministic validation is truthful, localized
  documents are accepted without English boilerplate, and all isolated forward
  evaluations meet the predefined rubric thresholds.

## S6 - Language-Specific Rendering And Review

- [x] S6-T001: Extend renderer input with canonical language and model project
  title. Set HTML `lang`, escaped title, and edition metadata without changing
  neutral-v1 visual semantics. Covers G-R001..G-R002.
- [x] S6-T002: Render only a current passed validation for the selected edition
  and atomically write `<edition-key>.pdf`. Include edition/model/accounting/
  validation hashes in the render stage. Covers G-R001..G-R004, N002.
- [x] S6-T003: Preserve optional `p2p-engine[pdf]` behavior. Missing WeasyPrint or
  native dependencies must leave all prior stages untouched and report the
  selected edition and install guidance. Covers N009..N010, X021.
- [x] S6-T004: Refactor publication review to bind one edition's current
  Markdown, PDF, validation, model, accounting, language, and edition key. Covers
  G-R004..G-R006.
- [x] S6-T005: Prove approval is invalidated by any bound edition file change and
  never inherited by another language/output name even when source/model text is
  equivalent. Covers G-R004..G-R006, X013, X022.
- [x] S6-T006: Keep review owner-controlled and CLI-only. Ensure MCP catalog and
  handlers still expose no review write. Covers G-R006, G-R010.
- [x] S6-T007: Implement recorded default-English Markdown/PDF aliases only after
  successful v2 import/render. Alias writes are atomic, hashes are recorded, and
  aliases are never freshness inputs. Covers G-R015..G-R016.
- [x] S6-T008: Add tests proving Italian/custom editions cannot touch aliases and
  alias manual edits do not stale or approve the v2 edition. Covers G-R015..
  G-R016, X023.
- [x] S6-T009: Add renderer tests for English, Italian, regional tags, accents,
  tables, code, long chapters, page breaks, optional dependency failure, output
  collision, and atomic failure cleanup. Covers G-R001..G-R003, X018, X021.
- [x] S6-T010: Add review tests for approved, changes requested, missing PDF,
  stale validation, cross-language attempt, regenerated content, and legacy
  approval. Covers G-R004..G-R006, G-R014, X022..X023.
- [x] S6-T011: Update traceability and record renderer identity, HTML language,
  PDF hashes, alias behavior, and edition-specific review evidence.
- [x] S6-T012: S6 exit gate. Markdown, PDF, render status, and approval are
  isolated per edition; optional PDF failure and compatibility aliases cannot
  corrupt current state.

## S7 - CLI, MCP, Facade, Agent Lifecycle, And Documentation

- [x] S7-T001: Extend thin workspace facade methods for prepare/import/validate/
  render/review/status with keyword-only `language`, `output_name`, and relevant
  policy/source arguments. No-argument callers default to `project-en`. Covers
  G-R007, G-R011, N006.
- [x] S7-T002: Add CLI `--language` and `--output-name` to every edition command,
  `--contributions` to prepare, and model/accounting candidate arguments to
  import. Use shared core parsers and stable diagnostics. Covers G-R007,
  X001..X003.
- [x] S7-T003: Add read-only `p2p project publish list` and JSON output. Ensure
  `status` reports one selected edition while list reports all committed/legacy
  entries in stable order without generating or repairing files. Covers
  A-R007..A-R009, G-R008, N004.
- [x] S7-T004: Update CLI text/JSON result payloads with canonical language,
  edition key, output paths, candidate paths, evidence/model/accounting hashes,
  stale reasons, compatibility aliases, and corrective commands. Covers E-R010,
  G-R007..G-R008, N010..N011.
- [x] S7-T005: Update MCP catalog schemas for optional `language`, `output_name`,
  `contributions`, `model`, and `evidence_accounting`; add read-only list parity
  if exposed publicly. Covers G-R009.
- [x] S7-T006: Update MCP handlers to pass fields to facades and return the same
  edition semantics and diagnostics as CLI. Preserve write-safe derived-output
  classification and no review write. Covers G-R009..G-R010, N006.
- [x] S7-T007: Update MCP registry, tool-count/schema snapshots, permission/
  consent classification tests, and docs. Ensure optional fields remain backward
  compatible and required import companions are represented correctly. Covers
  G-R009..G-R010, G-R019.
- [x] S7-T008: Expand CLI tests for defaults, aliases, English/Italian coexistence,
  custom name, invalid identity, exact candidate help, text/JSON parity, list,
  status, import triplet, validation exit code, render, review, and root option.
  Covers G-R007..G-R008, AC001..AC002, AC016.
- [x] S7-T009: Expand MCP tests for prepare/import/validate/render/status/list in
  two languages and custom names, including stale/unsafe inputs and no review
  tool. Covers G-R009..G-R010, AC016.
- [x] S7-T010: Expand agent lifecycle tests for fresh install, update from v1,
  partial-resource repair, doctor drift, uninstall, multiple installed adapters,
  and generated instruction refresh. Covers G-R017, X024, AC017.
- [x] S7-T011: Update `README.md`, `docs/CLI-GUIDE.md`, `docs/CONCEPTS.md`,
  `docs/AGENT-INTEGRATION.md`, `docs/MCP.md`, and glossary/help sources where
  relevant. Document exact commands/paths, reader boundary, evidence sidecars,
  language tags, output name, contributions, review isolation, and legacy status.
  Covers G-R018, AC022.
- [x] S7-T012: Update release setup/templates/documentation that still name only
  `project.curated.md`, `project.pdf`, `curator-input.md`, or v1 template IDs.
  Preserve explicit compatibility-alias wording instead of implying those paths
  are v2 authority. Covers G-R013..G-R018.
- [x] S7-T013: Add a documentation consistency test that extracts every example
  path/command and compares it with resolver/CLI help contracts. Covers C-R017,
  G-R018, AC022.
- [x] S7-T014: Run public CLI, MCP, facade, agent lifecycle, documentation, and
  permission suites on Python 3.11 and current Python. Record command provenance.
- [x] S7-T015: Update traceability with public surface/test/doc evidence.
- [x] S7-T016: S7 exit gate. CLI, MCP, facades, generated agents, help, and docs
  describe one consistent multilingual edition workflow with no missing public
  argument or stale canonical path.

## S8 - Legacy Compatibility, Performance, Packaging, And Quality

- [x] S8-T001: Implement read-only discovery/classification of current v1
  unsuffixed profile, packet, curated Markdown, validation, PDF, review, and
  manifest. Report complete, partial, invalid, stale, and approved legacy
  summaries without importing them. Covers G-R014, X023.
- [x] S8-T002: Prove v1 approval is never copied into a v2 edition and no v1
  model/accounting completeness is invented. Document the required re-prepare,
  re-curate, import, validate, render, and review path. Covers G-R014..G-R016,
  X023, AC019.
- [x] S8-T003: Add compatibility tests for old facade calls, CLI defaults, MCP
  omitted optional fields, default-English aliases, v1 partial state, future v2
  contracts, and workspaces with no publication outputs. Covers G-R011..
  G-R016, X014, X023.
- [x] S8-T004: Add a workspace-schema regression proving schema v3 status,
  migration planning, runtime compatibility, and validation are unchanged by
  publication v2 artifacts. Covers G-R012..G-R013, AC018.
- [x] S8-T005: Re-run publication prepare/status/list profiles at 100, 1,000, and
  10,000 proposals. Compare with P baseline and record time, memory, reads,
  parses, lifecycle evaluations, vertical loads, evidence bytes, packet bytes,
  and per-edition marginal cost. Covers E-R011, N007, AC021.
- [x] S8-T006: Add structural performance assertions: one request context, one
  lifecycle batch, one vertical-memory load, no per-edition evidence rebuild,
  no full export embedding, and no deep freshness call in list. Covers E-R011,
  N007..N008.
- [x] S8-T007: Run duplicate-key YAML, C/Python loader parity, deterministic
  reversed-enumeration, process-restart, symlink, atomic-write, and read-byte-
  invariance suites. Covers N002..N005, N008.
- [x] S8-T008: Run static/type/lint/version checks defined by repository tooling
  and inspect new large functions/classes. Split orchestration or codecs that
  exceed local quality conventions instead of adding more behavior to
  `P2PWorkspace` or CLI/MCP handlers. Covers N006.
- [x] S8-T009: Build wheel and sdist from the source tree. Inspect archives for
  curator skill/reference templates, no live workspace/output files, optional
  PDF metadata, and correct package version. Covers G-R017, G-R019, N009,
  N012.
- [x] S8-T010: Install wheel and sdist into isolated Python 3.11 environments
  without source-path leakage. Run import provenance, init/agent lifecycle,
  English/Italian prepare/import/validate/status, MCP schemas, and optional PDF
  missing-capability smoke tests. Covers G-R019, N012..N013, AC020.
- [x] S8-T011: In an environment with PDF capability, run installed-artifact
  English/Italian render and inspect HTML language plus nonblank valid PDF
  outputs. Do not publish the artifacts. Covers G-R001..G-R003, G-R019.
- [x] S8-T012: Run focused, public, and full source suites on Python 3.11 and the
  current development Python with C and forced-Python YAML loaders. Record every
  pass/fail/skip and resolve feature regressions. Covers N012..N013, AC020.
- [x] S8-T013: Audit the Git diff for accidental `.p2p` writes, regenerated live
  outputs, cache/build artifacts, unrelated reversions, workspace schema change,
  database/provider dependencies, and release metadata. Covers N009, N014.
- [x] S8-T014: Update traceability and implementation evidence with legacy,
  performance, package contents, installed paths, Python, optional PDF, full
  suite, and residual-risk evidence.
- [x] S8-T015: S8 exit gate. Source and installed artifacts agree, Python 3.11 is
  supported, legacy state is honest, workspace v3 is unchanged, and measured
  read paths meet structural performance constraints.

## G - Final Implementation Gate

- [x] G-T001: Re-read the approved requirements/design and compare every public
  behavior against the implementation rather than task descriptions. Record
  deviations and either correct them or obtain explicit spec revision.
- [x] G-T002: Audit `traceability.md` row by row. Every A/B/C/D/E/F/G/N/X/AC
  item must have direct source, test/evaluation, and implementation-evidence
  links. No row may rely only on another requirement's evidence. Covers AC023.
- [x] G-T003: Verify the final reader boundary with fixture outputs: no proposal/
  decision/Change/Work IDs, governance chronology, readiness narration, source
  hashes/paths, mandatory `.p2p` authority boilerplate, or invented
  implementation state. Covers AC006..AC007, AC010, AC012.
- [x] G-T004: Verify multilingual invariants: default English, normalized tags,
  custom output name, independent paths/freshness/review, localized renderer,
  and same project scope across editions. Covers AC001..AC002, AC009,
  AC013..AC015.
- [x] G-T005: Verify evidence invariants: complete source catalog, unmapped
  evidence, stable IDs, full accounting, claim links, contribution totals, and
  no external contamination. Covers AC003..AC005, AC008, AC011.
- [x] G-T006: Verify all public CLI/MCP/agent/documentation/package contracts and
  compatibility behavior from installed artifacts. Covers AC016..AC022.
- [x] G-T007: Run the final focused, public, full, Python 3.11, current Python,
  C/Python loader, wheel, sdist, PDF available/unavailable, performance, and
  forward-evaluation matrix. Record exact commands and results.
- [x] G-T008: Review all warnings, advisories, skips, benchmark regressions,
  legacy files, and optional capability failures. Classify each as resolved,
  accepted residual risk, environment limitation, or M-only alignment work.
- [x] G-T009: Verify repository reads remain byte-invariant and no live
  `.p2p`/publication/agent generated artifact was aligned before owner approval.
- [x] G-T010: Complete `implementation.md` with delivered behavior, source and
  test inventory, evaluation summaries, performance comparison, compatibility,
  known limits, and exact M preview inputs.
- [x] G-T011: Final feature exit gate. AC001..AC024 have direct evidence, every
  required P/S/G task is checked, no workspace migration is implied, and source
  implementation is complete before repository alignment.

## M - Owner-Confirmed Repository Alignment

M is operational alignment for this repository. It is not required to prove the
source feature and must not begin before G passes and the owner reviews a dry
preview.

- [x] M-T001: Run read-only status for workspace schema/runtime, agent adapters,
  publication legacy/v2 editions, visible export, and current source/evidence
  fingerprints. Record baseline paths/hashes and confirm workspace schema v3.
  Covers G-R012..G-R014, G-R020.
- [x] M-T002: Produce an exact persistent-write preview listing generated agent
  resource updates, shared publication evidence/catalog writes, selected edition
  profile/packet/model/accounting/Markdown/validation/PDF/review paths, legacy
  aliases, stale files left untouched, and cleanup/recovery behavior. Covers
  G-R020, AC024.
- [x] M-T003: Ask the owner to confirm languages, output names, contribution
  policy, generated agent updates, whether PDFs should be rendered, and whether
  any current owner review should remain unapproved. Do not infer approval.
  Covers G-R005..G-R006, G-R020.
- [x] M-T004: Through supported agent lifecycle commands, update installed
  adapters and run doctor. Verify concise skill and all references are current;
  do not edit generated adapter files manually. Covers G-R017, X024, AC017.
- [x] M-T005: Prepare each confirmed edition through the CLI. Verify one shared
  current evidence index, exact candidate paths, no full-export embedding, and
  no cross-edition overwrite. Covers AC001..AC004, AC009.
- [x] M-T006: Run curator work for each edition using the generated skill and
  write only the exact candidate triplet. Review the model, complete accounting,
  reader document, rubric, contribution wording, and contamination boundary
  before import. Covers AC005..AC012.
- [x] M-T007: Import and validate each confirmed edition through supported CLI
  commands. Resolve errors without editing canonical `outputs/latest` targets by
  hand. Covers AC005..AC013, AC016.
- [x] M-T008: Render confirmed PDFs only when optional capability and owner
  intent are present. Verify language/title metadata, output names, nonblank
  files, and compatibility aliases for default English only. Covers AC002,
  AC014, G-R015..G-R016.
- [x] M-T009: Leave publication review unapproved unless the owner explicitly
  reviews the exact current edition. If instructed, record review separately per
  edition through CLI. Covers AC015, X022..X023.
- [x] M-T010: Run final publication list/status, agent doctor, workspace schema
  status, validation, Git diff classification, and byte/hash comparison against
  M-T001. Confirm no `.p2p` canonical state or workspace schema changed as a
  side effect. Covers G-R012, G-R020, AC024.
- [x] M-T011: Record M results and residual legacy files in `implementation.md`.
  Mark alignment complete only when every confirmed edition is current through
  its intended stage and all unapproved review states are explicit.
