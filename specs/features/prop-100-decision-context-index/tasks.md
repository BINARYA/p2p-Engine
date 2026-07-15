# Tasks - PROP-100 Decision Context Index

All tasks are initially unchecked. Mark a task complete only when its stated
code, test, measurement, documentation or observed public behavior exists.
Planning text alone is not implementation evidence.

## Delivery Order And Gates

| Slice | Depends on | Public behavior change |
| --- | --- | --- |
| Preparation | none | no |
| A - Domain, sources and proposal decisions | Preparation | no |
| B - Authority and topology | A | no |
| C - Retrieval and budgets | B | no |
| D - Performance remediation | A; may run beside B/C | no |
| E - Context packet, CLI and MCP | C and D exit gates | yes |
| F - Intake and proposal prompts | E | yes |
| G - Next actions and projections | B and E | internal/public projection compatibility |
| H - Freshness and manifests | A and C | only for materialized derived outputs |
| I - Cache decision | D and H measurements | no cache implementation |

Do not start a dependent slice while its required exit gate is failing.

## Gate And Preparation

- [x] T000: Confirm implementation authorization. Completion evidence is either
  owner acceptance of `PROP-100` or a separate explicit owner instruction to
  implement this repository feature despite proposal state. Refining this spec
  is not implementation authorization.
- [x] T001: Capture the current context performance baseline. Record elapsed
  time, call path, proposal/choice/Change Set/Work summary calls, registry calls,
  validation calls, filesystem discovery count and repeated file reads for one
  untargeted context and one `PROP-*` context. Completion is a checked-in
  implementation note or test artifact that identifies the dominant repeated
  work. Covers R073-R074.
- [x] T002: Create the source inclusion/authority/exclusion implementation
  matrix from the design. Completion lists every current source reader and
  classifies proposal/decision artifacts, choices, conflicts, Change Sets,
  vertical sources, governance precedents, project definition, Work,
  artifact-state/readiness/questions/contributions, registries, project
  projections, prompts and publication outputs. Covers R008-R010, R025-R033.
- [x] T003: Create the consumer compatibility matrix. Completion records current
  fields and behavior for context packet service, CLI text, CLI structured
  output, MCP `p2p_context`, intake rendering, proposal prompts, next actions and
  relation registries, including `PROP`, `CHANGE`, `CHOICE`, `WORK` and no-target
  cases. Covers R062-R067, N006.
- [x] T004: Freeze v1 constants before coding: source catalog, schema, extractor,
  authority, relation, lexical normalizer, retrieval and budget policy versions;
  relation vocabulary; diagnostic codes; score table; thresholds and budgets.
  Completion is versioned code data or test fixtures matching the design, not
  duplicated magic values. Covers R012, R026, R037, R046-R055, R059-R060.
- [x] T005: Establish focused commands and fixture factories. Completion is a
  documented command set for parser/domain, authority/topology, retrieval,
  performance, context/CLI/MCP, intake/prompts, next actions, freshness, public
  and full tests, plus reusable synthetic project builders. Covers AC001-AC015.
- [x] T006: Record the read-only filesystem invariant. Completion is a helper
  that snapshots canonical and derived project files before/after index
  build/query and reports any mutation. Covers R002, AC015.

## Slice A - Domain, Sources And Proposal Decisions

- [x] A001: Add typed enums/literals for source classification and presence,
  source kind, record/node/relation kind, canonicality, authority, activation,
  confidence, completeness, diagnostic severity/fatality, freshness and context
  budget. Completion includes accepted-value and invalid-value tests. Covers
  R011, R025, N007.
- [x] A002: Add immutable core contracts for `SourceDocument`, `ParsedFragment`,
  evidence, record, node, relation, diagnostic, index, retrieval request/policy/
  hit/packet and manifest. Completion proves immutable collection exposure and
  type-safe construction. Covers R011.
- [x] A003: Implement deterministic JSON-ready serializers with explicit schema
  versions. Completion tests enums, optional spans, dates/times, paths, empty
  collections and canonical ordering without relying on `repr` or generic
  `asdict` behavior. Covers R012, R063.
- [x] A004: Implement stable source, fragment, evidence and record identity
  helpers. Completion proves unchanged semantic slot stability, content-hash
  separation, root-relative path normalization, source-rename identity change,
  duplicate-section occurrences and independence from line number, mtime and
  enumeration order. Covers R013-R017.
- [x] A005: Implement the v1 `SourceCatalog` descriptor model and proposal/
  decision-only discovery. Completion proves deterministic paths, explicit
  expected/missing state, exclusion of registries/generated outputs and exactly
  one discovery pass. Covers R005, R008-R010.
- [x] A006: Implement request-scoped `SourceSnapshot` capture. Completion uses an
  injectable source accessor to prove each selected file is read once and that
  hash and parser consume the same bytes. Covers R005-R007, N003, AC002.
- [x] A007: Implement the captured-text Markdown parser. Completion table-tests
  LF, CRLF, heading spacing, fenced code blocks, duplicate headings, missing
  trailing newline, empty legacy placeholders, line spans and missing sections.
  Covers R018, E001-E004, AC003.
- [x] A008: Implement captured-text frontmatter/YAML parsing. Completion
  distinguishes absent, empty, malformed and wrong-shape data, exercises
  duplicate-key handling and proves no path reopen. Covers R019, E002, AC003.
- [x] A009: Implement deterministic proposal section-to-claim mapping. Completion
  covers single sections, top-level list splitting, nested list retention,
  repeated sections and empty placeholders for problem, goals, non-goals,
  proposal and acceptance criteria. Covers R017, R020.
- [x] A010: Implement proposal body extraction. Completion emits proposal-state
  and claim records with stable IDs, separate text hashes, evidence spans,
  exploratory/legacy activation and source completeness. Covers R020, R025.
- [x] A011: Implement decision extraction for accepted,
  accepted-with-changes, rejected, deferred, split, merged-into-other,
  superseded, pending and unknown legacy outcomes. Completion includes outcome,
  reason/qualifier, approver, date and evidence links to affected proposal
  claims. Covers R021-R023, AC004.
- [x] A012: Implement proposal-status/decision-outcome reconciliation.
  Completion proves decision authority wins only in the derived view, emits a
  stable divergence diagnostic and performs no source repair. Covers R024.
- [x] A013: Implement source/index completeness aggregation and diagnostic
  fatality. Completion proves malformed optional sources yield a partial useful
  index while missing governed root, duplicate owner identity and
  nondeterministic catalog failure stop the build. Covers R016, R075-R078.
- [x] A014: Add the stateless `ProjectDecisionContextService` facade and wire it
  behind `P2PWorkspace`. Completion proves a memoized service creates a new
  snapshot for each build and exposes no public CLI/MCP change. Covers R003-R004,
  N005, N011.
- [x] A015: Add same-workspace freshness and read-only tests. Modify a source
  through an existing test write surface between two facade calls and prove the
  second call sees new bytes; also prove build/query changes no file. Covers E005,
  AC008, AC015.
- [x] A016: Add `tests/test_decision_context_sources.py`, parser-focused tests
  and `tests/test_decision_context_service.py`; run them with bytecode/cache
  writes disabled where supported.
- [x] A017: Slice A exit gate. Confirm proposal/decision-only index output is
  deterministic under reversed source enumeration, first-slice code has no
  consumer/storage changes and all A tasks have direct evidence. Record files,
  tests and residual risks before Slice B/C integration work.

## Slice B - Authority And Topology

- [x] B001: Expand `SourceCatalog` descriptors for all v1 source families while
  preserving Slice A identities. Completion proves derived projections,
  publications, generated prompts and cache paths remain excluded. Covers
  R008-R010.
- [x] B002: Implement `SourceMetadataResolver` by combining the proposal-review
  artifact catalog, artifact-state entries, import/provenance metadata and source
  defaults. Completion proves an untracked artifact is not accidentally treated
  as owner-confirmed. Covers R028, E006.
- [x] B003: Implement the declarative versioned authority policy across separate
  canonicality, authority, activation, confidence and completeness axes.
  Completion asserts every authority rank and rejects unsupported combinations.
  Covers R025-R027.
- [x] B004: Add full lifecycle activation tests, including conditional
  acceptance qualifier, historical split/merge/supersession state, unresolved
  deferral and unknown legacy behavior. Covers R022-R024, AC004.
- [x] B005: Extract explicit decision precedents with proposal/choice/tag
  applicability references and dedicated precedent authority. Completion proves
  a precedent is project context but not an accepted proposal decision. Covers
  R031.
- [x] B006: Extract only cataloged governance rules, relevance criteria and
  project-definition fields. Completion has allow-list tests and proves generic
  unrecognized free text does not become an active constraint. Covers R032.
- [x] B007: Implement the typed node catalog and type-specific existence rules
  for proposal, decision, choice, Change Set, Work, vertical section,
  capability, surface, feature, command and file. Completion covers missing
  identity nodes and valid symbolic value nodes. Covers R034.
- [x] B008: Implement the v1 relation vocabulary, alias map, directed/symmetric
  identity and unsupported-type quarantine. Completion proves incoming/outgoing
  query direction does not duplicate edges. Covers R035-R037.
- [x] B009: Normalize Change Set accepted/included/referenced proposal and
  decision links plus Work lineage. Reconcile frontmatter and companion files,
  merge matching evidence and emit divergence diagnostics. Covers R038-R040,
  E009.
- [x] B010: Normalize `related-proposals.yml`. Completion covers every supported
  alias, source/target validation, self-relations, missing targets, evidence and
  activation inherited from source lifecycle. Covers R037-R041.
- [x] B011: Normalize `impact-map.yml` into capability, surface, feature, command
  and file value-node relations. Completion covers shape errors, duplicates,
  planned files and artifact authority. Covers R034, R038.
- [x] B012: Normalize proposal `conflict-analysis.yml` and project conflict
  memory. Completion covers symmetric conflict identity, winner/rejected
  evidence, historical state and incompatible assertions. Covers R036, R038-R041.
- [x] B013: Normalize project choices, selected options, choice links/blockers
  and proposal-local vote metadata. Completion proves local votes do not become
  unresolved project choice nodes or active blockers. Covers R027, R038, E007-E008.
- [x] B014: Normalize artifact-state, readiness, questions and contributions as
  evidence-quality/event records. Completion distinguishes owner-confirmed,
  system, agent-proposed, answered, applied and superseded states and proves
  readiness never activates a decision. Covers R028-R030.
- [x] B015: Normalize declared vertical coverage as explicit section relations
  and heuristic matches as retrieval signals only. Completion preserves
  declared/heuristic provenance and confidence. Covers R034, R038, R043.
- [x] B016: Normalize Work-to-Change execution state without changing proposal
  authority. Completion covers active/completed Work and missing Change targets.
  Covers R033, R038.
- [x] B017: Implement equivalent-edge merge and deterministic evidence ordering.
  Completion proves duplicate assertions score as one logical edge while all
  evidence and lifecycle states remain inspectable. Covers R040-R041, E010.
- [x] B018: Implement adjacency maps and cycle/fan-out-safe traversal primitives.
  Completion covers self-cycle, multi-node cycle, symmetric conflict and high
  fan-out termination. Covers R042, E011.
- [x] B019: Add malformed and divergent source tests for every Slice B extractor;
  prove unsupported relations and invalid targets become diagnostics rather than
  disappearing or entering active topology. Covers R075-R078, AC005.
- [x] B020: Run focused authority/topology tests and the Slice A regression set.
  Slice B exits only when all relation IDs and evidence order remain deterministic
  under reversed source enumeration and no public payload changed.

## Slice C - Explainable Retrieval And Budgets

- [x] C001: Implement versioned `RetrievalRequest`, `RetrievalPolicy`, scoring
  signal and budget-policy objects from T004. Completion proves all v1 limits,
  weights, caps and thresholds serialize once from shared policy data. Covers
  R044, R048, R053-R055.
- [x] C002: Implement lexical normalizer v1: NFKC, casefold, Markdown marker
  removal, punctuation splitting, fixed bilingual stop words and preservation of
  IDs/commands/paths. Implement the 60-percent ubiquitous-token threshold and
  domain/rare/normal token weights. Completion includes accented text, mixed
  case, paths, command names, empty/stop-word input, corpus-size boundaries and
  no locale/network dependency. Covers R046-R047, E012.
- [x] C003: Build immutable token, owner, authority, adjacency,
  capability/surface and vertical-section postings into
  `DecisionContextIndex`. Completion proves retrieval receives no path or source
  accessor. Covers R045, N004.
- [x] C004: Implement proposal-target candidate construction for direct
  relations, accepted decisions, decided choices, blockers/conflicts, declared
  capability/surface/vertical signals, lexical postings and bounded historical
  alternatives. Enforce accepted-decision/precedent applicability through an
  explicit relation, a declared domain match, or lexical contribution at least
  10 with a rare/domain token. Positive lexical query claims must exclude
  non-goals and historical rationale. Covers R044, R050-R053.
- [x] C005: Implement idea-text candidate construction. Completion proves only
  applicable project-wide precedents/constraints are attached and generic or
  stop-word-only input returns no arbitrary owners. Covers R046-R047, R057, E012.
- [x] C006: Implement v1 score arithmetic and relation-signal exclusivity.
  Completion golden tests reproduce every score from emitted contributions,
  exercise the exact weighted lexical-overlap formula, enforce per-group caps,
  prevent duplicate-edge multiplication and clamp to `0..100`. Covers R049,
  R053-R054, E010.
- [x] C007: Implement eligibility, authority ordering and tie-breaking.
  Completion covers minimum score 15, authority rank, explicit/heuristic,
  lifecycle, stable owner ID and canonical-date recency only when both dates
  exist. Covers R051-R055, E013-E014.
- [x] C008: Implement one-hit-per-owner grouping, target-self exclusion,
  deterministic duplicate-claim suppression and selected record/relation
  payloads. Completion proves a hit includes usable decision/constraint/claim
  content and evidence, not only an ID. Covers R050, R056.
- [x] C009: Implement historical threshold 35 and explicit historical
  conflict/alternative/lineage exceptions. Completion proves historical lexical
  overlap cannot outrank directly applicable active decisions by itself. Covers
  R051, E013.
- [x] C010: Implement cycle-safe transitive expansion with depth and fan-out
  limits. Completion proves `small` uses direct edges only and `medium` reports
  paths for at most one extra hop. Covers R042, R059-R060, E011.
- [x] C011: Implement exact `small` and `medium` assembly using canonical compact
  JSON UTF-8 byte measurement. Completion enforces every hit/record/relation/
  reason/depth/byte limit after ranking. Covers R058-R061.
- [x] C012: Implement deterministic truncation and truncation metadata.
  Completion proves retained claims keep minimum evidence and reports original
  versus retained counts. Covers R061, E018.
- [x] C013: Implement stable empty-neighborhood behavior and diagnostic/reason.
  Completion proves no first-N fallback and a JSON-ready empty packet. Covers
  R057, E012, E017.
- [x] C014: Add a readable synthetic golden corpus covering every proposal
  lifecycle state, accepted-with-changes, explicit/duplicate relations,
  conflicts, choices/local votes, precedents, Change Set divergence,
  artifact-state mismatch, vertical declared/heuristic signals and malformed
  optional sources. Covers AC004-AC006.
- [x] C015: Add adversarial retrieval tests for generic terms, duplicate common
  vocabulary, irrelevant early IDs, false-positive historical proposals,
  unsupported relations and missing dates. Covers E012-E014.
- [x] C016: Add metamorphic/invariant tests for reversed/random source order,
  repeated builds, contribution sum, score caps, duplicate evidence, cycles and
  budget monotonicity (`small` selected content is not made less relevant by
  assembling `medium`). Covers N001, N009, AC007.
- [x] C017: Prove source-free query execution using the injected access counter;
  candidate construction, scoring and budget assembly must perform zero
  filesystem reads. Covers R045, R073, AC002.
- [x] C018: Run focused retrieval tests plus all Slice A/B regressions. Slice C
  exits only when golden output, policy versions and byte budgets are stable and
  no existing public consumer uses the new service.

## Slice D - Performance Remediation Gate

- [x] D001: Turn T001 observations into an instrumented regression test for the
  current context call path. Completion identifies every repeated workspace
  scan/service reconstruction rather than recording elapsed time alone. Covers
  R073, N003-N004.
- [x] D002: Remove or bypass per-proposal full Change Set reconstruction in the
  relevant context/registry path. Completion proves Change Set records are built
  once per operation and indexed for proposal lookup. Covers R073, N003.
- [x] D003: Remove other profile-confirmed duplicate summary, registry,
  validation or next-action work from one context request without changing
  output. Completion has call-count assertions for the exact hotspots found in
  T001. Covers R073.
- [x] D004: Add source-access instrumentation to decision-index scale tests.
  Completion proves one discovery pass, one read/hash/parse per selected source
  and zero query reads. Covers R006, R073, AC002.
- [x] D005: Build the deterministic representative scale fixture with at least
  100 proposals, 25 Change Sets and 20 project choices plus local votes,
  conflicts, vertical mappings and malformed optional sources. Covers R074.
- [x] D006: Add the scale regression test for index build plus one proposal
  query. Completion satisfies the 5-second ceiling in the normal test
  environment and reports structural counters on failure. Covers R074, AC009.
- [x] D007: Re-run current context service, registry builder and next-action
  tests after remediation and prove existing output is unchanged. Covers N006.
- [x] D008: Slice D exit gate. Record before/after baseline and structural
  counters. Slice E is blocked until D002-D007 pass; elapsed-time waiver alone
  cannot override a repeated-scan failure.

## Slice E - Context Packet, CLI And MCP

- [x] E001: Extend the context core model with optional/versioned
  `nearby_context` while preserving every legacy field. Completion includes
  serialization tests before changing renderers. Covers R062.
- [x] E002: Inject the stateless decision-context facade into
  `ContextPacketService` through `P2PWorkspace` without direct source discovery
  in the consumer. Covers R003-R004, R062.
- [x] E003: Enable nearby retrieval only for valid `PROP-*` targets. Completion
  proves invalid proposal targets retain current error behavior and one request
  builds at most one decision index. Covers R044, R062.
- [x] E004: Implement context `small` behavior from the shared budget packet;
  completion asserts active decisions/constraints/blockers and exact limits,
  with no renderer-side selection. Covers R058-R060.
- [x] E005: Implement context `medium` behavior from the shared budget packet;
  completion asserts qualifiers, non-goals, rationale, historical alternatives,
  one-hop relations, provenance, diagnostics and freshness. Covers R058-R061.
- [x] E006: Add stable empty and partial nearby-context payloads with schema,
  policy, fingerprint, completeness and truncation metadata. Covers R016, R062.
- [x] E007: Add compatibility tests proving `CHANGE-*`, `CHOICE-*`, `WORK-*`, no
  target and all legacy context fields remain byte/structure compatible where
  public contracts require it. Covers R044, N006, AC011.
- [x] E008: Update CLI text rendering intentionally. Completion renders a compact
  nearby-decision section with owner, score and strongest reason, handles empty/
  partial state and never reranks/truncates. Covers R063.
- [x] E009: Update CLI YAML/JSON output tests. Completion proves the structured
  object matches service serialization and respects `small|medium`. Covers R063.
- [x] E010: Update MCP `p2p_context` output serialization and contract tests in
  the same change. Completion covers enums, optional paths/dates, empty/partial
  packets, parity with workspace output and unchanged input schema unless inputs
  actually changed. Covers R012, R063, AC011.
- [x] E011: Prove context integration is read-only with the before/after
  filesystem invariant and performs no decision-context cache/manifest write.
  Covers R002, R072, AC015.
- [x] E012: Run context service, CLI and MCP focused tests plus public tests.
  Completion records exact commands and confirms the Slice D performance
  counters still pass with integration enabled.
- [x] E013: Slice E exit gate. Verify public docs/payload examples match actual
  observed output, non-proposal behavior is unchanged and no new write surface
  was introduced.

## Slice F - Intake And Proposal Prompt Neighborhood

- [x] F001: Replace first-30/first-50 semantic registry selection in the intake
  context path with idea-text decision retrieval. Completion proves unrelated
  low-ID records disappear and relevant decisions/constraints appear. Covers
  R064.
- [x] F002: Preserve non-semantic project metadata needed by intake separately
  from nearby retrieval. Completion proves removing first-N selection does not
  remove required governance/status context. Covers R064, N006.
- [x] F003: Preserve controlled-apply boundaries. Completion proves retrieved
  duplicate/conflict/relation candidates are prompt context only and do not
  create contributions, choices, relations or canonical changes. Covers R064,
  AC012.
- [x] F004: Feed explore prompts bounded nearby decisions, constraints and
  alternatives with evidence references appropriate to exploration. Covers R065.
- [x] F005: Feed impact prompts normalized relation candidates, active conflicts,
  capability/surface/vertical context and artifact authority without treating
  heuristics as edges. Covers R043, R065.
- [x] F006: Feed synthesize prompts accepted/qualified constraints, decided
  choices and relevant historical alternatives without automating governance
  decisions. Covers R065.
- [x] F007: Apply phase-specific payload minimization. Completion proves prompts
  receive selected evidence and bounded diagnostics rather than the full index
  or full source contents. Covers R059-R061, R077.
- [x] F008: Update CLI/MCP contracts only for prompt/intake payloads actually
  exposed publicly; otherwise record an explicit no-public-change test. Covers
  R063-R065.
- [x] F009: Run intake lifecycle, project context renderer, proposal artifact,
  controlled-apply and MCP parity tests. Add adversarial prompt tests for generic
  ideas and conflicting historical alternatives.
- [x] F010: Slice F exit gate. Confirm no first-N semantic fallback remains in
  migrated paths, controlled apply is unchanged and prompt token/byte growth is
  bounded by policy.

## Slice G - Next Actions And Registry Projections

- [x] G001: Route next-action project-choice checks through normalized choice
  nodes/relations. Completion proves proposal-local vote metadata does not yield
  a project `resolve choice` action. Covers R066, AC013.
- [x] G002: Route next-action proposal/change relationship checks through the
  typed index where the semantics are supported. Completion avoids raw registry
  interpretation while preserving current action precedence. Covers R066.
- [x] G003: Add regressions for decided choices, missing choice targets, local
  votes, active blockers, historical conflicts and no-action cases. Covers
  R066, E007-E008.
- [x] G004: Keep current `relations.yml` as a legacy derived projection in this
  feature. Completion documents that normalized topology is internal and proves
  the decision index never reads the projection as semantic input. Covers R067.
- [x] G005: Do not add a normalized public relation registry under PROP-100.
  Completion records a follow-up requirement if users need that artifact,
  including schema/version/migration design before implementation. Covers R067.
- [x] G006: Expose topology diagnostics only through already-versioned read-only
  context/diagnostic surfaces; do not invent a durable diagnostic file. Covers
  R075-R078.
- [x] G007: Run next-action, registry-record builder and registry service tests;
  prove current registry projection output remains compatible and no projection
  feeds back into semantic extraction.
- [x] G008: Slice G exit gate. Confirm normalized semantics drive migrated next
  actions, legacy projections remain derived and public behavior changes are
  documented.

## Slice H - Freshness And Materialized Manifests

- [x] H001: Implement source fingerprint from catalog version plus sorted path,
  presence and captured-byte hash entries. Completion covers content change,
  file creation/deletion, same record count and enumeration-order invariance.
  Covers R068, E015.
- [x] H002: Implement index semantic fingerprint from source fingerprint plus
  extractor, authority and relation-policy versions. Completion proves each
  policy change invalidates semantics independently. Covers R069.
- [x] H003: Add retrieval and budget policy versions to context packets and
  semantic packet comparison. Covers R069.
- [x] H004: Inject the clock used for `generated_at` and exclude observational
  time from semantic equality/fingerprints. Completion builds twice with
  different clocks and obtains equal semantic output. Covers R070, AC014.
- [x] H005: Implement the derived manifest model for consumers that already
  materialize context projections. Completion serializes schema/generator/time,
  source and semantic fingerprints and sorted inputs without writing during
  ordinary index build. Covers R071.
- [x] H006: Implement stale comparison for source presence/hash, catalog,
  extractor, authority, relation, retrieval and budget versions as applicable to
  each projection. Completion returns actionable stale reasons. Covers R071,
  R075-R078.
- [x] H007: Use existing atomic write helpers only if an already-persistent
  consumer writes a manifest in its own integration path. Completion includes
  interrupted replacement/error tests; otherwise record that no materialized
  manifest is currently required. Covers R002, R071.
- [x] H008: Add same-workspace and no-write freshness regressions. Completion
  proves a second request after source change is fresh and index construction
  creates no manifest/cache. Covers R004, E005, AC008, AC015.
- [x] H009: Run focused freshness tests and all context public tests. Slice H
  exits only when generated time is observational and content/presence/policy
  changes are distinguishable.

## Slice I - Cache Decision, No Cache Implementation

- [x] I001: Measure index build time, query time, peak index size and source/read
  counters on the representative fixture and current project after Slice H.
  Covers R072-R074.
- [x] I002: Record one explicit result: `cache_deferred` when thresholds are met,
  or `separate_cache_feature_required` when measured rebuild/query cost is not
  acceptable. Include measurements and bottleneck evidence. Covers R072.
- [x] I003: If persistence is justified, stop cache implementation under this
  task list and create a separate repository specification covering path,
  atomicity, locking, invalidation, schema migration, corruption, cleanup and
  rebuild. Covers R072.
- [x] I004: Prove PROP-100 introduced no persistent cache path, cache cleanup
  command or cache-dependent correctness behavior. Covers R002, E016.
- [x] I005: Slice I exit gate. The feature can complete with `cache_deferred`; a
  cache implementation is never required for PROP-100 completion.

## Documentation And Traceability

- [x] J001: Update `docs/CLI-GUIDE.md` in the first slice that changes `p2p
  context`, intake or prompt behavior. Document nearby-context support, budgets,
  empty/partial state, diagnostics and source-of-truth boundary.
- [x] J002: Update `docs/MCP.md` with actual `p2p_context` output shape,
  read-only behavior, version/fingerprint fields and CLI/MCP parity.
- [x] J003: Add an implementation note after every delivered slice with files
  changed, tests/measurements, public impact, compatibility and residual risks.
- [x] J004: Maintain requirement/design/task traceability whenever implementation
  evidence changes a contract. Do not update only task wording when behavior,
  authority, schema or public payload changes.
- [x] J005: Document legacy `relations.yml` status and the explicit exclusion of
  registries, decisions map, generated project narratives, prompts,
  publications and caches from semantic extraction.

## Final Validation

- [x] V001: Run all decision-context unit/service tests, including sources,
  parser, authority, topology, retrieval, performance and freshness modules.
- [x] V002: Run context packet, project context renderer, intake lifecycle,
  proposal artifact, next actions, registry and MCP focused regression tests.
- [x] V003: Run `./scripts/test-public.sh` after every public integration and
  record the result.
- [x] V004: Run `./scripts/test-smoke.sh` and `./scripts/test-full.sh` before
  handoff; record an explicit residual risk if full validation cannot run.
- [x] V005: Run `.venv/bin/p2p validate` as a read-only project validation check
  after implementation.
- [x] V006: Review changed paths and command history to confirm no canonical
  `.p2p/` file was edited manually and no generated output became semantic input.
- [x] V007: Verify AC001-AC015 against direct evidence and leave every unmet task
  unchecked. Do not infer completion from a green broad test alone.
- [x] V008: Produce final performance evidence with before/after context
  baseline, structural counters, scale ceiling, index size and cache decision.

## Follow-Up Candidates

- [ ] X001: Evaluate embeddings only as an additive, explainable signal after v1
  deterministic retrieval is stable and measured.
- [ ] X002: Specify a persistent cache only if Slice I selects
  `separate_cache_feature_required`.
- [ ] X003: Specify normalized topology as a public/versioned registry only if a
  concrete consumer requires durable projection.
- [ ] X004: Extend retrieval to Change Set, Choice and Work targets in separate
  compatibility slices.
- [ ] X005: Revisit deeper vertical/governance interpretation only with explicit
  source contracts and authority rules.
