# Tasks - Vertical-Aware Project Memory Performance And Incremental Projection

All tasks are initially unchecked. Mark a task complete only when its stated
code, test, measurement, documentation, or observed public behavior exists.
Planning text alone is not implementation evidence.

## Implementation Discipline

- Execute tasks in dependency order. Do not start a dependent slice while its
  exit gate is failing.
- Keep `.p2p` writes behind supported P2P services and commands. Never repair or
  seed the feature by editing managed workspace files manually.
- Preserve unrelated owner changes in the working tree.
- Keep all read and benchmark operations byte-invariant.
- Update `traceability.md` after every slice. Do not wait for the final gate to
  reconstruct requirement -> design -> task -> test evidence.
- Record source import path, package version, Git revision, Python version,
  dataset, and cache mode for every performance result.
- Treat wall-clock targets as measured gates and structural operation counts as
  correctness gates.
- Do not implement SQLite, another database, a persistent query cache, or
  decision-memory semantic compaction in this feature.
- Treat local package builds and isolated installs as tests only. Do not commit,
  tag, push, release, upload, or publish as part of these tasks.

## Delivery Order

| Slice | Depends on | Main result |
| --- | --- | --- |
| P - Preparation | none | trustworthy baseline and traceability |
| A1 - Read context and source capture | P | one lazy request context |
| A2 - Schema and lifecycle batch | A1 | no quadratic ledger parsing |
| A3 - Vertical batch processing | A1, A2 | one pack load and linear coverage |
| A4 - Registry bundle contract | A1, A2 | trustworthy atomic read model |
| A5 - Fast command paths | A2, A3, A4 | common reads avoid deep work |
| A6 - Deep validation and YAML | A1, A2 | semantic parity with faster deep checks |
| A-G - Block A gate | A1..A6 | performance foundation accepted |
| B1 - Vertical-memory contracts | A-G | typed schema and artifact ownership |
| B2 - Full vertical-memory builder | B1 | deterministic complete candidate |
| B3 - Incremental builder | B2 | impact-scoped equivalent candidate |
| B4 - Persistence, status and fallback | B2, B3 | atomic read model and safe reads |
| B5 - Public refresh and mutation hooks | B4 | progressive post-commit updates |
| B-G - Block B gate | B1..B5 | projection accepted |
| C1 - Readiness convergence | B-G | readiness consumes structured memory |
| C2 - Context convergence | C1 | bounded vertical-aware context |
| C3 - Next-action convergence | C1, C2 | one shared input snapshot |
| C4 - Rendering and freshness convergence | C1..C3 | vertical-first project output |
| C-G - Block C gate | C1..C4 | consumers accepted |
| X - Persistence evaluation | A-G, B-G, C-G | evidence-backed storage outcome |
| G - Final feature gate | X | complete implementation evidence |
| M - Repository alignment | G, owner approval | current workspace derived state refreshed |

## P - Preparation And Baseline

- [x] P-T001: Re-read `requirements.md`, `design.md`, every source path named in
  Origin And Evidence, and these prior implementation records:
  `specs/features/prop-100-decision-context-index/implementation.md`,
  `project-readiness-convergence-workflow/implementation.md`,
  `workspace-schema-versioning-and-legacy-migration/implementation.md`,
  `proposal-decision-revision-and-revocation-lifecycle/implementation-evidence.md`,
  and `runtime-surface-and-derived-state-contract-closure/implementation.md`
  under `specs/features/`. Record any source behavior that invalidates a design
  assumption before editing code. Covers A-R001..004 and N004.
- [x] P-T002: Create
  `specs/features/vertical-aware-project-memory-performance-and-incremental-projection/implementation.md`
  with sections for environment, baseline, slice evidence, public behavior,
  compatibility, residual risks, and final results. Completion is the empty
  evidence structure plus current Git revision and source import path.
- [x] P-T003: Create `traceability.md` in the same feature directory. Seed every
  A/B/C/X requirement, N/E requirement, and AC with design decision, owning
  slice, planned test/evidence, and status columns. No requirement may be left
  without an owning task. Covers the Traceability Rule.
- [x] P-T004: Add or update a development import-provenance helper that reports
  `p2p_engine.__file__`, package version, Python executable, Python version, and
  Git root. Completion includes a test proving the helper distinguishes the
  current `src` tree from `.venv/.../site-packages`. Covers A-R001..002, AC001.
- [x] P-T005: Update local source-test scripts or their shared runner so focused,
  public, and full development tests import `src`. Preserve a separate installed
  artifact smoke path with no source override. Completion proves both modes and
  documents their commands. Covers A-R001..002, N010, AC021.
- [x] P-T006: Add deterministic fixture builders for 100 rich proposals, 1,000
  mixed proposals, and 10,000 minimal proposals. Fixtures must support schema v2
  reads, schema v3 multi-event ledgers, declared/unmapped coverage, conflicts,
  choices, Change Sets, project definition/questions, and reversed enumeration.
  Covers A-R003..004, N015..017.
- [x] P-T007: Add a reusable read-operation counter and benchmark harness. It
  must capture elapsed time, memory where practical, discovery, reads, hashes,
  parser contracts, schema checks, ledger parses, vertical loads, provider
  calls/cache hits, and canonical fallbacks. Covers A-R003..004.
- [x] P-T008: Capture source-tree baselines for `check`, `status`, proposal list,
  one decision status, registry show/status, project progress, untargeted and
  targeted small context, next top 3, validate, and project freshness. Run each
  in cold CLI and in-process modes; record median and a high percentile where
  practical. Covers N013..016.
- [x] P-T009: Profile baseline `status`, context, next, registry status, progress,
  and lifecycle aggregation. Record a call-graph table identifying all global
  work and repeated work, including current request-snapshot reuse already
  present in `src`. Covers AC002..005.
- [x] P-T010: Snapshot repository bytes before and after every preparation read
  and benchmark. Completion proves no persistent write, bytecode, cache, or
  generated output entered the repository from read-only measurements. Covers
  N002, AC019.
- [x] P-T011: Define focused test commands for A1..A6, B1..B5, C1..C4, scale,
  concurrency, CLI, MCP, docs, package, Python 3.11, public, and full suites in
  `implementation.md`.
- [x] P-T012: Preparation exit gate. Review baseline and traceability with all
  tasks still scoped to performance and vertical derived memory. Explicitly
  confirm that physical proposal compaction and database persistence remain out
  of scope.

## A1 - Request-Scoped Read Context And Source Capture

- [x] A1-T001: Add immutable core contracts for captured-document metadata,
  read consistency state, operation counters, provider keys, fast verification,
  and concurrent-change diagnostics. Completion includes construction,
  immutability, JSON-ready debug serialization, and invalid-state tests. Covers
  A-R005..013, N001, N008.
- [x] A1-T002: Implement `WorkspaceDocumentStore` with request-private byte
  capture, optional capture, deterministic directory discovery, text decoding,
  physical hashing, and loader-contract-aware parse memoization. Completion
  proves each selected path is physically read once. Covers A-R008..010.
- [x] A1-T003: Add explicit parser cache keys containing resolved path, captured
  physical hash, and loader contract. Prove a safe parse cannot satisfy a
  unique-key or decision-ledger parse request. Covers A-R009, A-R045.
- [x] A1-T004: Implement discovery snapshots that record sorted entry identity
  and metadata for proposal, Change Set, choice, Work, registry, project, and
  vertical directories selected by a provider. Completion covers add, remove,
  rename, symlink rejection, and reversed enumeration. Covers A-R010, E001.
- [x] A1-T005: Implement `WorkspaceReadContext` with lazy provider registration,
  argument-sensitive memoization, immutable values, counters, and explicit
  finalization. Constructing an unused context must perform zero source reads.
  Covers A-R005..007, AC002.
- [x] A1-T006: Implement optimistic consistency finalization over captured files,
  discoveries, and observed transaction-lock identity. Completion covers no
  change, source content change, same-size content change, addition, removal,
  and active mutation transaction. Prove write preconditions continue to use
  content/source identity rather than trusting mtime, size, or request cache.
  Covers A-R010..011, N005, E001.
- [x] A1-T007: Add one-retry orchestration to composite `P2PWorkspace` reads.
  Inject a mutation between providers and prove the first result is discarded;
  inject two changes and prove `P2P_READ_CONCURRENT_CHANGE` is returned without
  a mixed payload. Covers A-R011.
- [x] A1-T008: Add `P2PWorkspace.read_context()` and optional `read_context`
  parameters to selected internal facades without changing existing public
  callers. Completion proves compatibility wrappers create exactly one context
  per top-level read. Covers A-R012..013.
- [x] A1-T009: Adapt `DecisionContextSourceService` to consume captured source
  access through an adapter while preserving its one-discovery, one-read,
  one-hash, one-parse counters and request-private raw bytes. Covers A-R008,
  N003.
- [x] A1-T010: Adapt `ProjectReadinessSourceAccess` to delegate to the shared
  document store when a read context exists while preserving standalone tests
  and its current source-count evidence. Covers A-R008, A-R013.
- [x] A1-T011: Add `tests/test_workspace_document_store.py` and
  `tests/test_workspace_read_context.py` covering laziness, memoization,
  parser isolation, discovery, concurrency retry, process restart, and
  byte-invariance.
- [x] A1-T012: Run decision-context source/service, project-readiness source,
  transaction concurrency, context packet, and workspace facade regressions.
- [x] A1-T013: Update `traceability.md` with A1 code/test evidence and actual
  counter behavior before starting A2.
- [x] A1-T014: A1 exit gate. Every selected source is captured once, unused
  providers do no work, and concurrent reads cannot return mixed revisions.

## A2 - Schema Preflight And Batch Lifecycle

- [x] A2-T001: Add immutable `WorkspaceSchemaPreflight` and exact serializer.
  Include declaration state, current/target version, layout class, contract
  version, migration required, recovery required, and stable diagnostics limited
  to preflight concerns. Covers A-R014.
- [x] A2-T002: Refactor `WorkspaceSchemaService` into cheap `preflight()` and
  complete `status(preflight=..., read_context=...)`. Preserve current deep
  findings, migration support, alignment advisories, and recovery behavior.
  Covers A-R014, A-R018.
- [x] A2-T003: Add tests proving preflight reads no proposal ledger, vertical
  pack, registry, or project definition and complete status still detects every
  existing schema/layout finding. Covers A-R014..015.
- [x] A2-T004: Refactor `ProposalLifecycleAuthorityService` with one private
  `evaluate_many()` batch engine receiving preflight and captured documents.
  Normalize IDs and resolve proposal directories once. Covers A-R015..018.
- [x] A2-T005: Make single `status()` delegate to the shared evaluator and make
  `capture_all()` invoke one batch call. Preserve strict-mode exception and
  unresolved-view behavior. Covers A-R016..019.
- [x] A2-T006: Adapt `ProposalDecisionLedgerCodec` to parse captured bytes and
  report parser counts without reopening the path. Preserve unique keys,
  canonical field validation, event ordering, binding, semantic hashes, and
  diagnostics. Covers A-R008..009, A-R019.
- [x] A2-T007: Adapt schema v2 legacy projection capture to use the same selected
  source bytes and prove schema v2 read compatibility remains unchanged. Covers
  A-R019.
- [x] A2-T008: Pass one lifecycle map through workspace summaries, registry
  record building, validation, publication fingerprints, next actions, decision
  impact, and project state when they execute in one read context. Remove nested
  `capture_all()` calls. Covers AC002..003.
- [x] A2-T009: Refactor deep validation so workspace-schema ledger findings and
  proposal lifecycle findings share captured ledger parses. Preserve diagnostic
  ownership and prevent duplicate findings. Covers A-R018, A-R034.
- [x] A2-T010: Add single/batch semantic parity tests for every lifecycle event,
  malformed ledger, divergent projection, stale proposal binding, unknown
  legacy state, schema v2, migration recovery, and future schema. Covers E002,
  AC010.
- [x] A2-T011: Add structural scale tests asserting at most N ledger parses and
  one schema preflight for N selected proposals at 100, 1,000, and 10,000 scale.
  Assert no call to complete schema status inside the evaluator. Covers A-R018,
  N015, AC003.
- [x] A2-T012: Re-run proposal decision, migration, schema, validation, registry,
  publication, context, next-action, CLI, and MCP lifecycle tests.
- [x] A2-T013: Update traceability and implementation evidence with before/after
  lifecycle call counts and timings.
- [x] A2-T014: A2 exit gate. Lifecycle semantics are unchanged, targeted status
  reads one ledger, and aggregate cost grows linearly.

## A3 - Batch Vertical Coverage And Progress

- [x] A3-T001: Add immutable `VerticalReadState` with active selection, resolved
  pack, valid section IDs, normalized section terms, term frequencies, compiled
  patterns, and policy versions. Covers A-R020..023.
- [x] A3-T002: Add one read-context provider keyed by vertical ID, profile, and
  modules. Prove one active-state load and one pack load per key across progress,
  readiness, coverage status, and suggestions. Covers A-R020.
- [x] A3-T003: Implement batch declared-coverage capture and validation. Parse
  each existing coverage artifact once, classify absent/invalid/mismatch/valid,
  and retain path-specific diagnostics. Covers A-R021..022, E003.
- [x] A3-T004: Make single proposal coverage status a wrapper over the batch
  evaluator or shared private evaluator. Preserve current public status states
  and payload fields. Covers A-R021.
- [x] A3-T005: Implement one heuristic term model per vertical pack and one batch
  suggestion evaluator. Precompile regexes once and capture each selected text
  file once. Preserve scoring, suppression, evidence, and ordering semantics.
  Covers A-R023.
- [x] A3-T006: Add explicit heuristic computation state `computed`,
  `not_requested`, or `unavailable` to internal/result contracts where omission
  would otherwise look like an empty authoritative set. Covers A-R024..025.
- [x] A3-T007: Refactor `ProjectProgressService.status()` to receive proposal,
  vertical, definition, coverage, and optional heuristic snapshots. Default
  authoritative progress must not require heuristics. Covers A-R024, A-R033.
- [x] A3-T008: Preserve independent definition and declared-evidence axes,
  optional/not-applicable exclusions, blockers, questions, assumptions, and
  warning behavior. Add parity golden tests. Covers C-R003..006.
- [x] A3-T009: Add batch parity tests comparing legacy single-proposal coverage
  and heuristic behavior against the new engine for valid, invalid, missing,
  multi-section, base-extended, and custom packs. Covers E003.
- [x] A3-T010: Add structural performance tests proving one pack load, bounded
  regex compilation, one selected-source read, and linear proposal processing at
  100, 1,000, and 10,000 scale. Covers N015.
- [x] A3-T011: Re-run vertical pack, vertical lock, project definition,
  readiness, progress, coverage, migration, CLI, and MCP tests.
- [x] A3-T012: Update traceability and record progress timing with heuristics
  disabled and enabled.
- [x] A3-T013: A3 exit gate. Authoritative progress does not compute heuristics,
  and all vertical work is batch and request-scoped.

## A4 - Versioned Atomic Registry Bundle

- [x] A4-T001: Define immutable registry bundle manifest contracts, generator
  and source-catalog policy constants, validation, JSON-ready serialization, and
  unsupported-version diagnostics. Covers A-R036..040, E012.
- [x] A4-T002: Define the exact canonical source catalog per registry and one
  combined registry bundle catalog. Include only files whose bytes or semantics
  affect generated records. Add catalog inclusion/exclusion golden tests. Covers
  A-R036..037.
- [x] A4-T003: Implement deterministic physical/semantic source fingerprints
  and per-scope fingerprints independent from root, mtime, observation time, and
  enumeration order. Cover same-count, same-size, rename, addition, removal, and
  unrelated-source cases. Covers A-R037..038, E004.
- [x] A4-T004: Refactor registry record generation into one pure candidate
  renderer consuming supplied lifecycle and source snapshots. Preserve all
  existing fields and ordering. Covers A-R043.
- [x] A4-T005: Render `manifest.yml` with source identity, output digests, counts,
  and owned paths after all registry candidates exist. Validate candidate
  internal counts and source policy versions. Covers A-R036.
- [x] A4-T006: Replace separate registry `write_text` calls with one
  `AtomicMutationWriter` transaction over all owned files. Add candidate
  validation, source preconditions, idempotent no-op behavior, stale-output
  deletion policy, and changed-path results. Covers A-R039, N007.
- [x] A4-T007: Implement registry status from manifest shape, output digests, and
  current source fingerprint without semantic record reconstruction. Add stable
  reasons for current, stale, missing, invalid, unsupported, and mixed output.
  Covers A-R039..040, E005.
- [x] A4-T008: Implement read-context registry-view cache-aside behavior. Current
  uses materialized records; stale/missing/invalid/unsupported uses canonical
  in-memory batch fallback or explicit unavailable result and writes nothing.
  Covers A-R041..042, N012.
- [x] A4-T009: Preserve compatibility when legacy registry files exist without a
  manifest: classify them as unverifiable legacy/stale, permit canonical
  fallback, and recommend refresh. Do not infer current from counts alone.
- [x] A4-T010: Add failure injection before staging, after staging, during each
  replacement, after manifest candidate, and during rollback. Prove old complete
  generation, new complete generation, or recovery-required state only. Covers
  E005..006, AC008.
- [x] A4-T011: Add concurrent reader/refresh tests proving no reader accepts a
  mixed generation as current. Covers A-R039, E005.
- [x] A4-T012: Update registry CLI/MCP serializers and docs with additive
  manifest version, source fingerprint, status, and reason fields. Text output
  remains concise.
- [x] A4-T013: Re-run registry, validation, context, next, project state,
  publication, migration, CLI, MCP, transaction, and recovery tests.
- [x] A4-T014: Update traceability and record old reconstruction counts versus
  new fingerprint/status counts and elapsed time.
- [x] A4-T015: A4 exit gate. Same-count changes are detected, refresh is atomic,
  and current registry status does not reconstruct semantic records.

## A5 - Fast Status, List, Progress, Context, And Next Paths

- [x] A5-T001: Add a shared cost-class catalog for public reads with `fast`,
  `targeted`, and `deep` plus allowed provider sets. Add a source audit test that
  maps every public composite read to one class. Covers A-R026.
- [x] A5-T002: Add typed `FastFreshnessSummary` from schema preflight,
  transaction/recovery status, registry manifest, vertical-memory manifest when
  available, and existing projection manifests. It must not build publication,
  software-spec, decision-index, progress, or complete freshness state. Covers
  A-R027..035.
- [x] A5-T003: Refactor workspace `status` to one read context and fast providers.
  Preserve project name and proposal output compatibility, add verification
  metadata, and remove implicit complete freshness. Covers A-R027, A-R035.
- [x] A5-T004: Refactor proposal list to current registry records with lifecycle
  batch fallback. Preserve status filtering, ordering, title, and text output.
  Covers A-R028, A-R041.
- [x] A5-T005: Wire project progress to the A3 request snapshots and default
  declared-only heuristic mode. Add an explicit internal or public option only
  where detailed heuristic output is required. Covers A-R024..025, A-R033.
- [x] A5-T006: Refactor `ContextPacketService` to accept one read context instead
  of constructing an eager untyped snapshot. Keep target normalization and
  budget validation unchanged. Covers A-R005, A-R029..032.
- [x] A5-T007: Remove complete validation from small context. Add verification
  states and preserve explicit validation command guidance. Prove no validation
  findings are falsely claimed. Covers A-R029, A-R035.
- [x] A5-T008: Remove complete freshness from small context. Use fast freshness
  and preserve an explicit command for complete analysis. Covers A-R029.
- [x] A5-T009: Make untargeted small context consume current registry/project
  compact state and skip full decision-context construction. Preserve targeted
  proposal nearby retrieval with at most one index build. Covers A-R030..031.
- [x] A5-T010: Refactor `NextActionService` query entry points to receive typed
  request inputs or the read context. Remove callback paths that rebuild index,
  freshness, lifecycle, summaries, readiness, or changes already loaded. Covers
  A-R032.
- [x] A5-T011: Preserve all existing next-action classes, remediation semantics,
  active Change Set coverage, stable IDs, ordering, curated actions, readiness
  actions, and limits. Add provider-count assertions around list and refresh.
  Covers C-R016..020.
- [x] A5-T012: Add fast-path structured output fields to CLI and MCP serializers
  without breaking existing keys. Update CLI/MCP docs and source agent templates
  to distinguish fast status from explicit validation/freshness.
- [x] A5-T013: Add `tests/test_fast_read_paths.py` with forbidden-provider spies
  for status, proposal list, progress, untargeted/targeted small context, and
  next top 3. Covers AC005.
- [x] A5-T014: Add byte-invariance tests for every fast path and retry/fallback
  branch. Covers A-R048, AC019.
- [x] A5-T015: Run context, next, status, proposal, registry, progress, readiness,
  decision-context, CLI, MCP, docs, and generated-template regressions.
- [x] A5-T016: Update traceability and record source-tree before/after provider
  counts and elapsed times for every N013 command.
- [x] A5-T017: A5 exit gate. No fast command invokes a forbidden deep provider,
  and outputs state exactly what was and was not verified.

## A6 - Shared YAML Contracts And Deep-Path Optimization

- [x] A6-T001: Inventory every `yaml.safe_load`, `yaml.load`, custom loader,
  frontmatter parse, and YAML round trip in `src`. Classify required loader
  semantics and record migration exclusions. Covers A-R044..047.
- [x] A6-T002: Implement project-owned safe Python and C loader classes and
  foundation helpers for mapping, sequence, arbitrary safe value, and unique-key
  documents. C loader use must be feature-detected. Covers A-R044..045, N011.
- [x] A6-T003: Port unique-key constructors for decision ledger, decision impact,
  decision context, and other specialized readers to matching C/Python loader
  contracts. Preserve exact duplicate diagnostics. Covers A-R045.
- [x] A6-T004: Adapt generic validation and compatible source readers to shared
  helpers and captured documents. Do not mechanically replace migration tag
  loaders or semantic YAML round trips without parity evidence. Covers A-R046.
- [x] A6-T005: Refactor complete validation to one read context. Share generic
  parse results with readiness/questions/artifact validators where the same
  loader contract suffices; reuse captured bytes otherwise. Covers A-R034,
  A-R046.
- [x] A6-T006: Add parity corpora for mappings, sequences, scalars, null, Unicode,
  anchors, aliases, merge keys, duplicate keys, malformed indentation, tags,
  multi-document input, and very large YAML. Compare C and Python results and
  errors. Covers A-R047.
- [x] A6-T007: Run all migration, decision ledger, decision context, readiness,
  vertical, permissions, registry, validation, and serialization tests once with
  C loader available and once forcing Python fallback. Covers N010..011.
- [x] A6-T008: Measure parsing of the real current YAML set and complete validate
  before/after. Record parser counts and timing without using a narrow CI-only
  threshold. Covers N014.
- [x] A6-T009: Audit direct YAML calls remaining after the refactor and document
  each justified specialized use.
- [x] A6-T010: Update traceability and implementation evidence.
- [x] A6-T011: A6 exit gate. Deep findings are unchanged, duplicate-key semantics
  are preserved, Python fallback passes, and complete validation performs no
  duplicate generic source reopen.

## A-G - Block A Completion Gate

- [x] A-G-T001: Run all A1-A6 focused tests together and resolve fixture,
  ordering, monkeypatch, loader-mode, and read-context interactions.
- [x] A-G-T002: Run structural 100, 1,000, and 10,000 proposal tests. Record
  counts proving no proposal-count-squared path and bounded provider work.
  Covers N015, AC003..005.
- [x] A-G-T003: Run cold source CLI and warm in-process/MCP benchmarks for all
  N013-N014 commands. Record median, p95, memory, source, and environment.
- [x] A-G-T004: If an N013 target fails, profile the remaining cost and either
  correct Block A or record a justified blocker before B implementation. Do not
  hide a failed target by relaxing it without evidence.
- [x] A-G-T005: Run source audits proving fast paths cannot call complete
  validation/freshness and lifecycle/vertical loops cannot call global status or
  pack loaders.
- [x] A-G-T006: Run byte-invariance, concurrency retry, registry transaction,
  malformed-source, reversed-order, and Python-fallback suites.
- [x] A-G-T007: Run public CLI/MCP tests and the complete suite against `src`.
- [x] A-G-T008: Run Python 3.11 supported-version checks and installed wheel/sdist
  smoke tests separately from source tests.
- [x] A-G-T009: Complete Block A traceability rows and review actual source diff
  for unrelated refactors, cache artifacts, direct `.p2p` edits, or public
  compatibility drift.
- [x] A-G-T010: Block A exit gate. AC001..008 applicable to Block A and all
  A-R/N/E requirements have direct evidence; B may begin.

## B1 - Vertical Project-Memory Contracts And Ownership

- [x] B1-T001: Add versioned immutable core contracts for manifest, aggregate
  project, section definition, contribution, evidence, conflict, diagnostic,
  status, view, impact, operation result, pagination, and derived update. Covers
  B-R001..017, B-R038..042.
- [x] B1-T002: Implement strict validators and JSON-ready serializers for the
  exact `manifest.yml`, `project.yml`, and section shapes in design. Reject
  unknown contract versions, unsafe paths, duplicate section IDs, duplicate
  contribution IDs, invalid hashes, and absolute paths. Covers B-R002..003,
  E008, E012.
- [x] B1-T003: Define constants for generator, source catalog, authority,
  contribution identity, ordering, diagnostics, and section schema versions.
  No duplicated magic version strings across builder/status/serializer code.
- [x] B1-T004: Implement safe owned-path construction rooted exactly at
  `.p2p/project/vertical-memory/`; section paths must derive from validated pack
  IDs. Add traversal, symlink, absolute, and stale-owned-path tests. Covers
  B-R001..002, N006..007.
- [x] B1-T005: Define source-scope catalogs for definition, questions, proposals,
  decisions, declared coverage, relations, and choices/conflicts. Prove derived
  registries, vertical memory itself, publication, software specs, and Work
  implementation state are excluded as authority sources. Define contract and
  source-fingerprint checks for any derived accelerator. Covers B-R004..008,
  B-R042.
- [x] B1-T006: Add the `vertical_project_memory` node and dependency edges to the
  freshness catalog without implementing generation. Update canonical-source
  enumeration to prove the nested derived directory is excluded. Covers B-R037.
- [x] B1-T007: Define stable contribution identity using existing
  decision-context record/evidence identity where available and a documented
  vertical identity helper otherwise. Test independence from line number,
  enumeration, root, and mtime. Covers B-R009..010, N001.
- [x] B1-T008: Define deterministic ordering for sections, active/historical
  contributions, evidence, conflicts, diagnostics, assumptions, questions,
  blockers, and unmapped proposals. Add golden ordering tests.
- [x] B1-T009: Create synthetic golden schemas covering one complete section,
  one partial section, multi-section proposal, unmapped active proposal,
  historical lineage, unresolved conflict, heuristic suggestion, and malformed
  source diagnostic. Include a large source artifact proving the schema stores
  only exact material fragments and references.
- [x] B1-T010: Add `tests/test_vertical_project_memory_contracts.py` and run core,
  serializer, safe-path, freshness-graph, and source-classification tests.
- [x] B1-T011: Update traceability and implementation evidence.
- [x] B1-T012: B1 exit gate. Artifact ownership, schema, identity, authority
  boundary, and dependency direction are fixed before builder code begins.

## B2 - Deterministic Full Vertical-Memory Builder

- [x] B2-T001: Implement a pure `VerticalProjectMemoryBuilder.build_full()` that
  receives one read context and returns complete candidate bytes plus typed
  view, fingerprints, source preconditions, and diagnostics without writing.
  Covers B-R018, B-R025.
- [x] B2-T002: Build active vertical, lock, pack, definition, questions,
  lifecycle, and decision-context inputs once from the supplied read context.
  Assert provider counts and prove stale/missing/invalid/unsupported registry or
  decision-context accelerators fall back to captured authority sources without
  semantic change. Covers B-R004, B-R006, B-R042, AC025.
- [x] B2-T003: Implement active contribution selection from current lifecycle
  authority, current proposal binding, decision-context activation, and explicit
  declared coverage. Cover accepted and accepted-with-changes. Covers B-R006,
  B-R009..013.
- [x] B2-T004: Implement historical contribution selection for revoked,
  rejected, withdrawn, deferred, superseded, split, merged, replaced, and
  previously accepted material only when explicit prior/current topology maps it
  to the section. Covers B-R008, B-R015, AC010.
- [x] B2-T005: Preserve proposal head event, authority, activation, rationale,
  constraints, goals, non-goals, acceptance criteria, source fragment, hashes,
  and lineage in contribution records. Extract only the smallest exact material
  fragment and never copy a complete proposal or artifact body by default.
  Prove no implementation status is inferred. Covers B-R007, B-R009..010,
  B-R038.
- [x] B2-T006: Implement multi-section placement with one contribution authority
  identity and section-specific applicability. Bound duplication to explicit
  declared sections and prove occurrences do not become separate decisions.
  Cover duplicate declared sections and invalid target quarantine. Covers
  B-R011, B-R039, E008.
- [x] B2-T007: Implement aggregate unmapped active proposal records and bounded
  diagnostics. Do not place heuristic-only proposals in authoritative section
  evidence. Covers B-R012..014, AC011.
- [x] B2-T008: Attach definition fields, assumptions, questions, blockers, and
  exact source identity to each section without copying computed readiness gaps.
  Covers B-R009, C-R002..006.
- [x] B2-T009: Attach explicit choices, conflicts, winners/rejected directions,
  supersession, split/merge, revocation, and reinstatement evidence. Preserve
  unresolved conflicts and do not choose a winner. Covers B-R015..016, E009.
- [x] B2-T010: Render every active vertical section even when it has no proposal
  evidence. Do not confuse definition-complete/no-evidence with missing section.
  Covers AC009.
- [x] B2-T011: Compute deterministic per-scope and aggregate source fingerprints,
  section output digests, aggregate output, and manifest after all candidates
  exist. Exclude observation metadata from bytes. Covers B-R003, B-R025,
  B-R028.
- [x] B2-T012: Add candidate internal validation: every aggregate section
  reference resolves, every owned output is declared, every contribution source
  is root-relative, every active proposal basis matches lifecycle selection, and
  output digests match bytes. Reject embedded complete artifacts and forbidden
  downstream payload classes according to the compactness contract.
- [x] B2-T013: Add golden tests for the current 19-section software vertical,
  base vertical, one custom vertical, and one extended vertical. Covers E003.
- [x] B2-T014: Add reversed/random enumeration and repeated-build tests proving
  complete byte equality and one-read/provider bounds. Run with network/model
  access disabled, fixed and varied locale, and varied wall-clock date to prove
  none affect output. Covers B-R025, N001, N018.
- [x] B2-T015: Add `tests/test_vertical_project_memory_service.py` with every
  lifecycle, coverage, mapping, conflict, definition, question, and malformed
  source case. Include multi-section large-artifact size and linear-growth
  assertions. Covers AC023.
- [x] B2-T016: Run decision-context, lifecycle, vertical, readiness-source,
  project-definition, conflict, choice, and relation regressions.
- [x] B2-T017: Update traceability and implementation evidence with candidate
  examples and source/provider counts.
- [x] B2-T018: B2 exit gate. Full candidate is complete, deterministic,
  authority-correct, vertical-complete, and side-effect free.

## B3 - Impact Classification And Incremental Equivalence

- [x] B3-T001: Implement pure `VerticalMemoryImpactClassifier` over exact changed
  paths, prior valid projection, active vertical state, and optional typed
  decision operation. Return scopes, sections, aggregate impact, full-rebuild
  flag, and stable reasons. Covers B-R019..022.
- [x] B3-T002: Implement exact impact rules for active vertical/lock/pack,
  definition, assumptions, blockers, project questions, proposal content,
  decision ledger/head/binding, coverage, relation, conflict, and choice changes.
  Add one table test per design row. Covers B-R020..022.
- [x] B3-T003: Implement previous/new section impact for coverage changes using
  source preimage and candidate bytes. If prior membership is unavailable or
  invalid, require full rebuild. Covers B-R021.
- [x] B3-T004: Implement proposal decision event impact using exact declared
  coverage and operation lineage. Cover accept, revoke, reinstate, supersede,
  split, merge, reject, defer, and no-op. Covers B-R020.
- [x] B3-T005: Implement safe broad/full fallback for ambiguous relation,
  vertical, definition, or invalid prior projection changes. Never understate
  affected sections. Covers B-R022.
- [x] B3-T006: Implement pure incremental builder that validates prior manifest
  and reused section digests, rebuilds affected sections with the B2 renderer,
  reuses unchanged bytes, and rebuilds aggregate/manifest candidates. Covers
  B-R023.
- [x] B3-T007: Reject incremental mode when generator/policy/vertical versions,
  checksums, source catalogs, owned paths, or reused output digests are
  incompatible. Fall back to full build with a stable reason. Covers B-R023,
  E012.
- [x] B3-T008: Add full-versus-incremental byte equivalence tests for every
  impact class and combinations affecting multiple sections. Covers B-R024,
  AC012.
- [x] B3-T009: Add property/metamorphic mutation sequences: create, accept,
  coverage move, edit definition, add conflict, revoke, reinstate, supersede,
  switch vertical, and remove stale section. Compare incremental output to a
  fresh full builder after every step. Covers B-R024..025.
- [x] B3-T010: Add scale measurements for no-op, one-section, multi-section, and
  full rebuild at 100, 1,000, and 10,000 proposal scale. Assert incremental work
  does not parse unrelated proposal sources after impact is known.
- [x] B3-T011: Add `tests/test_vertical_project_memory_incremental.py` and run B1,
  B2, lifecycle, coverage, definition, question, relation, and conflict suites.
- [x] B3-T012: Update traceability and implementation evidence with equivalence
  matrix and fallback reasons.
- [x] B3-T013: B3 exit gate. Every supported impact class is equal to full build;
  uncertainty broadens impact rather than returning incomplete current state.

## B4 - Atomic Materialization, Status, And Canonical Fallback

- [x] B4-T001: Implement `VerticalProjectMemoryService.status()` with manifest
  validation, output existence/digest checks, current source-scope fingerprints,
  and exact current/stale/missing/invalid/unsupported reasons. It must not render
  section semantics. Fingerprint mismatch diagnostics must identify stable
  changed scopes and paths where available. Covers B-R033..036, E007.
- [x] B4-T002: Implement pure full/incremental candidate selection from status
  and impact. Current no-op returns `unchanged`; invalid/unsupported prior state
  selects full rebuild without trusting prior bytes.
- [x] B4-T003: Implement atomic refresh over complete owned current/candidate
  paths with source preconditions, candidate workspace validation, stale-output
  deletion, one retry on source drift, and idempotent no-op. Covers B-R026..028.
- [x] B4-T004: Add vertical-switch tests that delete previous owned sections and
  write the new complete section set in one transaction. Covers B-R027, AC013.
- [x] B4-T005: Add failure injection through render-to-commit drift, staging,
  candidate validation, replacement, manifest, rollback, and recovery. Prove
  prior/new/recovery states only. Covers B-R026, E006, AC008.
- [x] B4-T006: Implement `WorkspaceReadContext.vertical_memory()` with the exact
  materialized/current, stale, missing, invalid, unsupported, canonical fallback,
  and fallback-failure matrix from design. Authority-sensitive fallback failure
  must stop with validation/refresh remediation rather than returning partial
  current state. Covers B-R029, B-R034..036, E011.
- [x] B4-T007: Ensure canonical fallback uses the B2 pure builder, writes nothing,
  reports `canonical_fallback`, and returns the same typed view as materialized
  files. Covers B-R035..036, N012.
- [x] B4-T008: Add display-only opt-in for labeled stale last-known data. Keep
  readiness, context current direction, and governance-sensitive consumers on
  current materialized or canonical fallback only. Covers B-R035.
- [x] B4-T009: Integrate vertical memory into complete derived freshness with
  correct output patterns, source scopes, dependencies, rebuild command, and
  downstream propagation. Prove it is not canonical input. Covers B-R037.
- [x] B4-T010: Add concurrent reader/refresh and source-change-before-commit tests
  using existing lock/recovery primitives. Covers N007, E001, E006.
- [x] B4-T011: Add byte-invariance tests for status, show, fallback, failed
  candidate validation, and unsupported version. Covers B-R029, AC019.
- [x] B4-T012: Run transaction, freshness, project-state, decision-context,
  vertical, readiness, recovery, and concurrency regressions.
- [x] B4-T013: Update traceability and implementation evidence with status table,
  failure results, and full/incremental timing.
- [x] B4-T014: B4 exit gate. Materialized state is atomic and optional, status is
  explainable, and canonical fallback is correct and side-effect free.

## B5 - Public Project Memory And Post-Commit Derived Updates

- [x] B5-T001: Add `p2p project memory status --format text|json` using the
  read-only status service. Text must show state, vertical, source fingerprint,
  section/output counts, reasons, and refresh command without dumping all
  sources. Covers B-R029..036.
- [x] B5-T002: Add `p2p project memory show --section SECTION-ID --format
  text|json` with `--include-history`, `--limit`, and `--cursor`; omitted section
  shows aggregate, exact section shows one bounded record page, and unknown
  section fails without fuzzy matching. Return total/returned/truncated/cursor
  metadata and deterministic page boundaries. Covers B-R009, B-R040, E008.
- [x] B5-T003: Extend `p2p project refresh` to render and atomically apply vertical
  memory through the same service while preserving existing project projection
  outputs and return behavior. Define operation ordering and failure reporting so
  one owned bundle cannot be mistaken for another's success. Covers B-R030.
- [x] B5-T004: Add read-only MCP status/show parity. If refresh MCP support is
  implemented, classify it as explicit write-safe, apply runtime/schema
  preflight, and return changed paths. No MCP read may refresh. Covers N008.
- [x] B5-T005: Add a shared `DerivedUpdateResult` adapter for post-commit
  vertical-memory updates with exact states and additive serialization. Preserve
  stable field names and compatibility behavior for callers that ignore the
  additive object. Covers B-R031..032, N009.
- [x] B5-T006: Integrate post-commit incremental update after proposal decision
  accept/revoke/reinstate/supersede/split/merge apply. Canonical commit result
  must be finalized before derived refresh starts. Attempt only no-op or proven
  incremental refresh against a current compatible generation; otherwise return
  stale/not-applicable plus explicit refresh. Covers B-R020, B-R031..032,
  B-R041.
- [x] B5-T007: Inject derived refresh failure after successful decision apply and
  prove canonical event/head/binding remains committed, response reports failed,
  status reports stale, and explicit refresh repairs it. Covers E010, AC014.
- [x] B5-T008: Integrate post-commit updates after vertical coverage apply,
  project definition apply, project readiness question convergence apply, and
  active vertical selection/reconciliation. Use exact changed paths and semantic
  operation details. Prove a vertical switch or incompatible contract reports
  stale instead of hiding a full rebuild. Covers B-R021..022, B-R031..033,
  B-R041, AC024.
- [x] B5-T009: Prove unrelated Change Set status, Work status, software spec,
  publication, generated export, and repository code changes do not alter
  vertical project memory unless cataloged project intent changed. Covers B-R007
  and the impact matrix.
- [x] B5-T010: Add external/Git-change tests that bypass post-commit hooks and
  prove source fingerprint marks materialized memory stale. Covers B-R033.
- [x] B5-T011: Update CLI guide, MCP guide, glossary, architecture docs, project
  skills/templates, and source-of-truth language. State clearly that vertical
  memory is derived and acceptance is not implementation.
- [x] B5-T012: Add CLI/MCP/public-contract tests for status/show/refresh,
  unsupported versions, stale labels, exact section identity, write safety, and
  no hidden read writes. Include default bounds, stable cursors, explicit history,
  and invalid cursor/limit behavior. Covers B-R040.
- [x] B5-T013: Run proposal decision, vertical coverage, definition convergence,
  project questions, project refresh, CLI, MCP, consent/write safety,
  transaction, and docs tests.
- [x] B5-T014: Update traceability and implementation evidence with every
  post-commit operation and failure behavior.
- [x] B5-T015: B5 exit gate. Project memory progresses after supported canonical
  changes, refresh failure never changes authority, and all public reads remain
  side-effect free.

## B-G - Block B Completion Gate

- [x] B-G-T001: Run all B1-B5 tests with all Block A regressions and resolve
  shared read-context, transaction, fingerprint, and serializer interactions.
- [x] B-G-T002: Run the complete lifecycle x coverage x vertical-section matrix,
  including active/historical/unmapped/conflict/question/definition states.
- [x] B-G-T003: Run full/incremental equivalence under randomized mutation
  sequences and reversed enumeration. Covers AC009..014.
- [x] B-G-T004: Run failure injection, rollback, recovery, concurrent read/write,
  external change, unsupported contract, and canonical fallback suites.
- [x] B-G-T005: Run source audits proving no project-memory reader writes, no
  builder grants authority, no heuristic enters declared evidence, and no
  implementation state enters project intent. Prove no complete source artifact
  or independently derived consumer payload is embedded in vertical memory.
- [x] B-G-T006: Benchmark materialized load, status, canonical fallback, no-op,
  one-section incremental, multi-section incremental, and full rebuild.
- [x] B-G-T007: Generate a candidate vertical memory for the current repository
  in local scratch only, compare it with active vertical/definition/lifecycle
  evidence, and record discrepancies without writing `.p2p`.
- [x] B-G-T008: Run public CLI/MCP, docs/templates, Python 3.11, package, and full
  suites against `src` and installed artifacts.
- [x] B-G-T009: Complete Block B traceability and review diffs for invented
  authority, schema migration, direct `.p2p` writes, observation timestamps, or
  unstable ordering.
- [x] B-G-T010: Block B exit gate. AC009..014 and all B requirements have direct
  evidence; consumer migration may begin.

## C1 - Readiness And Progress Convergence

- [x] C1-T001: Add a pure adapter from `VerticalProjectMemoryView` to
  `ProjectReadinessSnapshot`, preserving vertical identity, definition facts,
  active declared evidence, heuristic information, assumptions, blockers,
  questions, unmapped proposals, diagnostics, source hashes, and policy versions.
  Covers C-R001..009.
- [x] C1-T002: Keep `ProjectReadinessGapService` independent from vertical-memory
  builder code. Add an architecture/source audit preventing reverse imports or
  computed gaps inside vertical-memory files. Covers C-R002.
- [x] C1-T003: Build a transition parity corpus comparing the existing canonical
  source snapshot and projection-backed snapshot for every section and gap field.
  Resolve differences explicitly rather than updating golden output blindly.
  Covers C-R003..008, AC015.
- [x] C1-T004: Preserve separate definition and declared-evidence axes, all
  exclusions, no aggregate-authority percentage, and declared-only numerator.
  Add direct regression assertions. Covers C-R003..006.
- [x] C1-T005: Add readiness diagnostics/gaps for unresolved active conflicts,
  invalid projection, unavailable fallback, and stale authority according to
  existing severity policy. Do not let heuristic or rendered prose satisfy them.
  Covers C-R006..007.
- [x] C1-T006: Refactor project readiness ordinary path to current materialized
  memory or canonical in-memory candidate from the read context. Remove the
  duplicate ordinary global source scan after parity passes. Covers C-R001.
- [x] C1-T007: Implement optional internal affected-section classification and
  prove the final ordered readiness result equals full classification. If it
  provides no measured benefit, document and defer it without weakening B
  incremental memory. Covers C-R008.
- [x] C1-T008: Preserve bounded/paginated informational legacy and unmapped
  proposal detail in readiness review/gaps/questions surfaces. Covers C-R009.
- [x] C1-T009: Refactor project progress to consume the same memory/definition
  facts and preserve A3 batch fallback. Compare materialized and fallback output.
- [x] C1-T010: Update readiness CLI/MCP structured payloads only where additive
  projection state/source fields are needed. Preserve question and convergence
  command behavior.
- [x] C1-T011: Add `tests/test_project_readiness_vertical_memory.py` and run all
  readiness, progress, project questions, definition convergence, vertical,
  context, next-action, CLI, and MCP regressions.
- [x] C1-T012: Update traceability and implementation evidence with parity
  matrix and axis results.
- [x] C1-T013: C1 exit gate. Readiness consumes structured memory without a
  dependency cycle or authority change, and materialized/fallback results match.

## C2 - Context And Retrieval Convergence

- [x] C2-T001: Define a compact vertical-memory context assembler with exact
  section ordering, section count, contribution count, text/byte budgets,
  truncation metadata, and source-reference minimums for small and medium
  contexts. Covers C-R010..015.
- [x] C2-T002: Refactor untargeted small context to aggregate vertical memory,
  projection-backed readiness, registry summaries, and bounded next actions from
  one read context. Assert zero complete decision-index, validation, freshness,
  publication, and software-spec builds. Covers C-R010, C-R015, AC016.
- [x] C2-T003: Refactor proposal-targeted context to build at most one decision
  context, identify exact related vertical sections, retrieve bounded nearby
  evidence, and frame hits against current section memory. Covers C-R011..013.
- [x] C2-T004: Preserve target support and relevant artifact behavior for PROP,
  CHANGE, CHOICE, WORK, and no target. Non-proposal targets must not trigger
  proposal-only neighborhood logic.
- [x] C2-T005: Preserve active/historical authority ordering and explicit access
  to relevant revoked, superseded, conflicting, or alternative evidence. Ensure
  current direction never cites an inactive decision as active. Covers C-R012.
- [x] C2-T006: Add verification metadata for vertical memory, canonical fallback,
  readiness, validation, and freshness. Cover current, stale, missing, invalid,
  rebuilt in memory, not run, and fallback failure. Covers C-R014.
- [x] C2-T007: Enforce computation budgets with provider counters in addition to
  serialized token/byte budgets. A small context must not perform optional
  heuristic or publication work. Covers C-R015.
- [x] C2-T008: Add golden contexts for complete project, partial section,
  unmapped active proposal, revoked target, unresolved conflict, stale
  materialization with successful fallback, and fallback failure.
- [x] C2-T009: Add structural performance tests at current, 1,000, and 10,000
  scale for untargeted and targeted contexts. Assert zero query filesystem reads
  after decision-index build.
- [x] C2-T010: Update context CLI/MCP serializers, docs, agent templates, and
  prompt guidance to read compact project memory before full artifacts.
- [x] C2-T011: Run context, decision-context, retrieval, readiness, next,
  project-memory, CLI, MCP, intake, and prompt tests.
- [x] C2-T012: Update traceability and implementation evidence with provider and
  payload counts.
- [x] C2-T013: C2 exit gate. Small context bounds both work and output, remains
  traceable, and targeted retrieval keeps current authority semantics.

## C3 - Next-Action Convergence

- [x] C3-T001: Add immutable `NextActionInputs` and one read-context assembler
  containing schema preflight, fast freshness, lifecycle, compact topology or
  decision index, readiness, Change Sets, intakes, and curated actions. Covers
  C-R016..020.
- [x] C3-T002: Remove unrestricted provider callbacks from the ordinary
  `NextActionService.list()` path after compatibility wrappers assemble inputs.
  Assert no hidden global rebuild. Covers C-R016.
- [x] C3-T003: Generate project gap actions from structured readiness only.
  Preserve stable identities, severity ranking, question/apply/reconcile
  commands, and ten-gap bound. Covers C-R017.
- [x] C3-T004: Generate decision remediation from one lifecycle/impact/freshness
  snapshot. Preserve dependency-kind/status ordering and no automatic rollback
  implication. Covers C-R018.
- [x] C3-T005: Add one stable project-memory refresh/repair action when current
  structured memory cannot be obtained. Suppress section-dependent actions until
  current memory or canonical fallback exists. Covers C-R019.
- [x] C3-T006: Preserve active Change Set actions for every non-terminal Change
  Set, open choice blockers, curated actions, intake fallback, proposal readiness
  fallback, and top-limit behavior. Covers C-R020.
- [x] C3-T007: Add invariance tests for unrelated proposal additions, reversed
  source order, stale registry fallback, current/stale memory, repeated reads,
  and context embedding. Covers C-R020, AC017.
- [x] C3-T008: Add provider-count tests proving next inside context performs zero
  additional lifecycle, decision-index, freshness, readiness, registry, and
  proposal-summary builds.
- [x] C3-T009: Update next CLI/MCP docs only for additive refresh action and
  verification/source behavior.
- [x] C3-T010: Run next-action, decision impact, readiness, Change Set, choice,
  context, CLI, MCP, and project-memory regressions.
- [x] C3-T011: Update traceability and implementation evidence.
- [x] C3-T012: C3 exit gate. Next actions are deterministic, complete, bounded,
  and consume one caller snapshot.

## C4 - Vertical-First Project Rendering And Freshness

- [x] C4-T001: Define vertical-first rendering policy for existing overview,
  problem, scope, decisions map, feature compatibility outputs, visible export,
  and publication input. Map each output section to structured memory fields.
  Covers C-R021..025.
- [x] C4-T002: Refactor `ProjectStateService` pure render functions to consume a
  current `VerticalProjectMemoryView` plus existing project metadata. Do not read
  proposal directories independently once supplied. Covers C-R021.
- [x] C4-T003: Render current direction by vertical section and separate
  historical context, pending owner decisions, risks, assumptions, blockers,
  missing evidence, conflicts, and legacy unmapped material. Covers C-R022.
- [x] C4-T004: Preserve compact proposal/event/source references for every
  material decision or constraint and deterministic ordering. Covers C-R023.
- [x] C4-T005: Preserve existing generated feature directories and public project
  projection fields for compatibility, but stop treating their flat order as the
  primary project narrative.
- [x] C4-T006: Add explicit state labels and source-of-truth language proving
  rendered output is derived and does not establish governance, readiness,
  implementation, or publication approval. Covers C-R024, AC018.
- [x] C4-T007: Require current materialized or canonical in-memory vertical
  memory before project refresh/export. Cover stale labeled display, successful
  fallback, fallback failure, and no silent stale publication. Covers C-R025.
- [x] C4-T008: Update project projection manifest source fingerprint to bind the
  vertical-memory semantic source and preserve existing accepted-proposal
  ownership checks.
- [x] C4-T009: Update derived freshness graph so vertical memory staleness
  propagates to project projections, readiness/progress, context summaries,
  visible export, and publication without making ordinary fast status compute
  the complete graph.
- [x] C4-T010: Add golden vertical-first output tests for software, base, custom,
  partial, conflict, unmapped, and historical projects. Assert no chronological
  proposal dump and no implementation inference.
- [x] C4-T011: Add project refresh/export/publication failure and atomicity tests
  around stale or failed vertical memory. Preserve owner publication review.
- [x] C4-T012: Update publication curator packet guidance and generated project
  skills to consume vertical-first current project state while retaining `.p2p`
  as source of truth.
- [x] C4-T013: Run project state, visible export, publication, readiness,
  freshness, project-memory, CLI, MCP, docs, and generated-template tests.
- [x] C4-T014: Update traceability and implementation evidence with before/after
  output structure and source claims.
- [x] C4-T015: C4 exit gate. Current project output is vertical-first, traceable,
  authority-safe, and freshness-aware.

## C-G - Block C Completion Gate

- [x] C-G-T001: Run all C1-C4 tests with complete A/B regressions and resolve
  dependency, serializer, fallback, and freshness interactions.
- [x] C-G-T002: Compare readiness, progress, context, next actions, and project
  output from current materialized memory versus canonical in-memory fallback.
  Semantic outputs must match except explicit source-state metadata.
- [x] C-G-T003: Run stale/missing/invalid/unsupported/fallback-failure matrices
  across readiness, context, next actions, rendering, export, and publication.
- [x] C-G-T004: Run lifecycle authority audit proving revoked/rejected/withdrawn/
  replaced material cannot appear as active direction or active constraint.
- [x] C-G-T005: Run evidence audit proving heuristics and prose cannot satisfy
  readiness or declared coverage.
- [x] C-G-T006: Run performance tests for every N013-N014 command after consumer
  convergence and compare with Block A results.
- [x] C-G-T007: Run concurrent MCP read/write and post-commit derived failure
  suites across context, next, readiness, and memory status.
- [x] C-G-T008: Run public CLI/MCP, docs/templates, Python 3.11, package, and full
  suites against source and installed artifacts.
- [x] C-G-T009: Complete C traceability and review diffs for circular
  dependencies, hidden writes, stale-as-current output, duplicated authority,
  and unrelated scope expansion.
- [x] C-G-T010: Block C exit gate. AC015..019 and all C requirements have direct
  evidence; persistence evaluation may begin.

## X - File-Backed Persistence Evaluation

- [x] X-T001: Create `persistence-evaluation.md` with the exact evidence sections
  defined in design and no predetermined outcome. Covers X-R001..009.
- [x] X-T002: Record final source/import provenance, hardware, OS, filesystem,
  Python versions, Git revision, dataset generators, artifact counts, and command
  invocations.
- [x] X-T003: In deterministic fixtures or a disposable current-workspace copy,
  measure cold separate CLI process median/p95 for status, proposal list,
  registry status, progress, untargeted/targeted context, next, validate,
  freshness, memory status/show, project refresh no-op, and full rebuild.
- [x] X-T004: Measure persistent MCP first request, steady warm requests,
  post-mutation request, concurrent reads, and concurrent read/write retry.
- [x] X-T005: Measure current, 1,000, and 10,000 fixtures for source discovery,
  reads, hashes, parses, provider hits, memory load, canonical fallback, full
  build, one-section and multi-section incremental build, output size, and peak
  memory. Covers X-R002..005.
- [x] X-T006: Compare measured values with N013-N017 and structural gates.
  Attribute each miss to parsing, source discovery, hashing, serialization,
  process startup, index construction, projection load, or another measured
  component.
- [x] X-T007: Select `filesystem_sufficient` when all correctness/complexity
  gates and accepted targets pass without process-cache-dependent correctness.
  Document remaining optional optimizations. Covers X-R006..007.
- [x] X-T008: Otherwise select `persistent_index_feature_required` and document
  exact bottleneck, affected commands, required invalidation/recovery/migration,
  expected benefit, and why file-backed incremental state is insufficient.
  Covers X-R006, X-R008.
- [x] X-T009: Audit dependencies, repository paths, docs, and outputs to prove no
  SQLite/database package, persistent query cache, cache directory, migration,
  cleanup primitive, or hidden correctness dependency was introduced. Covers
  X-R009, AC022.
- [x] X-T010: Update traceability and implementation evidence with the selected
  outcome and direct measurement links.
- [x] X-T011: X exit gate. Exactly one outcome is recorded and justified; no
  persistence implementation exists.

## G - Final Feature Gate

- [x] G-T001: Review requirements, design, tasks, implementation, traceability,
  and persistence evaluation against final code. Resolve every unchecked or
  unsupported claim; planning text is not evidence.
- [x] G-T002: Complete the final requirement -> design -> task -> test/evidence
  matrix for A/B/C/X, N, E, and AC requirements. Confirm it was maintained at
  slice exits rather than reconstructed only now.
- [x] G-T003: Run all focused suites together, then public and full suites with
  source import provenance asserted.
- [x] G-T004: Run Python 3.11 and current-development Python checks, static/type/
  lint/version checks defined by repository tooling, and C/Python YAML loader
  modes.
- [x] G-T005: Build wheel and sdist, inspect package contents, install into an
  isolated environment, and run CLI/MCP smoke tests without `PYTHONPATH=src`.
  Prove installed import path and version. Keep every artifact local and do not
  commit, tag, push, upload, or publish it.
- [x] G-T006: Run final current/1,000/10,000 structural and performance gates,
  concurrent read/write, transaction failure, canonical fallback, reversed
  enumeration, byte-invariance, and deterministic rebuild suites.
- [x] G-T007: Run source audits for deep calls in fast paths, global calls inside
  per-proposal loops, direct YAML bypass, read-time writes, direct `.p2p` edits,
  heuristic authority, implementation inference, stale-as-current output, and
  database/cache additions.
- [x] G-T008: Review all CLI/MCP/docs/generated-template terminology for
  canonical source, derived registry, vertical memory, readiness axes, current
  direction, historical direction, and explicit deep validation.
- [x] G-T009: Review Git diff and generated outputs, preserving unrelated owner
  changes and excluding temporary profiles, benchmark datasets, bytecode,
  caches, build output, and scratch candidates.
- [x] G-T010: Record final public behavior, compatibility changes, performance,
  artifact contracts, recovery behavior, persistence outcome, and residual risks
  in `implementation.md`.
- [x] G-T011: Final feature exit gate. AC001..025 have direct evidence, no
  required task is unchecked, and no workspace alignment is implied before M.

Gate evidence: Python 3.11.15 ran in the official `python:3.11-bookworm`
container against a read-only host checkout copied into container scratch. The
full source suite passed with 1,331 tests and one expected optional-PDF skip;
wheel/sdist verification and the independently installed wheel smoke also
passed. Python 3.14 and both YAML loader modes are recorded in
`implementation.md`.

## M - Current Repository Derived-State Alignment

These tasks operate only after engine completion. They are not code
implementation evidence and require the normal supported P2P write surfaces.

- [x] M-T001: Inspect current repository runtime/schema compatibility, migration
  recovery, registries, active vertical/lock, definition, coverage, project
  memory status, freshness, and Git diff without writing.
- [x] M-T002: Confirm no workspace schema migration is required solely for the
  optional derived vertical-memory artifact. If code changes made it mandatory,
  stop and add an explicit migration design instead of editing `.p2p` manually.
- [x] M-T003: Run project-memory full candidate generation in no-write or scratch
  mode and compare section IDs, active proposal authority, mapping, conflicts,
  assumptions, questions, blockers, and unmapped proposals with canonical
  sources. Record discrepancies.
- [x] M-T004: Obtain owner confirmation before the first persistent current-
  repository registry/project refresh if the exact operation and generated
  targets have not already been authorized.
- [x] M-T005: Refresh the registry bundle through `p2p registry refresh`; verify
  atomic manifest, counts, source fingerprint, and current status.
- [x] M-T006: Refresh project projections and vertical memory through
  `p2p project refresh`; verify manifest, every active section, aggregate state,
  output digests, and no stale owned sections.
- [x] M-T007: Re-run project progress, readiness, untargeted/targeted context,
  next actions, validation, complete freshness, visible export status, and
  publication status. Do not infer publication approval.
- [x] M-T008: Compare current-repository fast/deep timings with Block X and
  explain material deviations.
- [x] M-T009: Review final workspace and repository diff. Confirm only expected
  generated derived outputs changed, canonical proposal/decision/definition/
  coverage authority did not change, and unrelated owner changes remain intact.
- [x] M-T010: Record current-repository alignment evidence and residual stale,
  missing, owner-controlled, or legacy state in `implementation.md`.
- [x] M-T011: M exit gate. Current workspace is aligned through supported
  primitives, or remaining misalignment is explicitly owner-controlled or
  documented without manual managed-state repair. This gate does not authorize
  source release or remote publication.
