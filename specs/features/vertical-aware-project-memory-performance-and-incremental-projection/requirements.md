# Requirements - Vertical-Aware Project Memory Performance And Incremental Projection

## Purpose

Make P2P Engine project memory fast to read and capable of representing the
current project by active vertical section as accepted proposal decisions
accumulate, change authority, or become historical.

The feature has four delivery blocks:

1. Block A removes repeated global computation from ordinary reads.
2. Block B creates a structured, vertical-aware, incrementally rebuildable
   project-memory projection.
3. Block C makes readiness, context, next actions, and project rendering consume
   that projection without changing their authority rules.
4. Block X measures the result and decides whether file-backed derived state is
   sufficient. It does not implement SQLite or another database.

The blocks share one architecture and final quality gate, but Block A must be
independently deliverable. Performance remediation must not depend on the
vertical-memory projection being complete.

## Origin And Evidence

This feature follows a read-only audit of the current source tree and the real
project workspace. The audit found that the workspace contains approximately
102 proposals, 2,994 `.p2p` files, 1,396 YAML files, and about 17 MB of data.
That volume is not sufficient to explain the observed latency.

The source audit basis is explicit:

- `src/p2p_engine/storage/filesystem.py` for public workspace orchestration;
- `src/p2p_engine/services/lifecycle_authority.py` and
  `workspace_schema.py` for lifecycle/schema repetition;
- `src/p2p_engine/services/project_verticals.py`, `project_progress.py`, and
  `project_readiness.py` for vertical and readiness processing;
- `src/p2p_engine/services/registries.py`, `workspace_status.py`,
  `context_packets.py`, `next_actions.py`, and `derived_freshness.py` for
  composite read costs;
- `src/p2p_engine/services/decision_context_sources.py`, `project_state.py`, and
  `workspace_transactions.py` for reusable source-capture, projection, and
  atomic-write patterns;
- `src/p2p_engine/cli_commands/project_ops.py`, `project_status.py`, and
  `registry.py` for the existing public commands extended by this feature.

Measured dominant behaviors include:

- `ProposalLifecycleAuthorityService.capture_all()` invokes per-proposal
  `status()`, and each `status()` recomputes full workspace-schema status.
- workspace-schema v3 layout validation parses every proposal decision ledger,
  producing quadratic ledger parsing during proposal aggregation;
- project progress repeatedly resolves active vertical state and reloads
  packaged vertical data while evaluating proposals;
- project progress and readiness recompute legacy coverage heuristics across
  unmapped proposals for ordinary reads;
- `p2p status`, `p2p context --budget small`, and `p2p next` compose validation,
  registry reconstruction, freshness, decision context, readiness, and other
  global operations even when their output is bounded;
- registry status reconstructs source records and primarily compares record
  counts, while registry files have no complete source-fingerprint and atomic
  bundle contract;
- local `.venv/bin/p2p` can import an installed package copy that differs from
  the current `src` tree while reporting the same package version, invalidating
  development benchmarks unless import provenance is checked.

Request-local reuse simulated against the current source reduces proposal
summary aggregation below one second and project progress to approximately two
seconds, but composite source-code paths remain materially slower:

| Operation | Approximate elapsed time after limited request-local reuse |
| --- | ---: |
| workspace status | 10.4 seconds |
| context small | 16.0 seconds |
| next actions without a supplied context | 14.1 seconds |
| project progress | 2.2 seconds |

For `context small`, residual cumulative costs are approximately 4.4 seconds
for deep validation, 4.2 seconds for full freshness, 2.5 seconds for registry
status, 1.8 seconds for decision-context construction, and 1.7 seconds for next
actions. The feature must remove unnecessary work, not merely cache the same
global call graph.

## Terms

- **Canonical source**: governed Markdown or YAML whose content carries project
  intent, authority, definition, owner evidence, or lifecycle state.
- **Read context**: one request-scoped, lazy, memoized and consistency-checked
  view over workspace sources and derived read models.
- **Captured document**: immutable bytes and physical identity read once by a
  read context for a specific path.
- **Fast path**: an ordinary query that reads only the minimum data needed and
  does not run global semantic validation or the complete freshness graph.
- **Deep path**: an explicit verification command that may scan and validate
  all relevant sources.
- **Read model**: derived, non-authoritative state optimized for queries and
  fully rebuildable from canonical sources.
- **Vertical project memory**: the structured read model that organizes current
  and historical project evidence by active vertical and section.
- **Rendered project narrative**: human-readable output derived from structured
  project memory. It is never an authority or readiness source by itself.
- **Declared coverage**: owner-confirmed proposal-to-vertical-section mapping.
- **Heuristic coverage**: advisory section matching inferred from text. It never
  counts as authoritative evidence.
- **Full rebuild**: deterministic reconstruction of the complete vertical
  project-memory read model from current sources.
- **Incremental rebuild**: deterministic reconstruction of only the affected
  section records and aggregate manifest.
- **Source scope**: a named dependency domain such as proposals, decisions,
  relations, vertical definition, project questions, or configuration.

## Goals

- Make common CLI and MCP reads fast at the current project scale.
- Eliminate quadratic and repeated global work.
- Establish one typed request-level read context instead of ad hoc snapshot
  dictionaries.
- Preserve strict, explicit deep validation for commands that require it.
- Reuse existing generated state safely through versioned, fingerprinted and
  atomically committed read-model contracts.
- Build a current project view around the active vertical rather than a flat
  chronological proposal list.
- Preserve proposal, decision-event, lineage, rationale, constraint and source
  traceability in every compact project-memory record.
- Keep project-definition completeness and accepted-evidence coverage as
  separate readiness axes.
- Make full and incremental vertical-memory rebuilds semantically equivalent.
- Retain file-backed operation unless measured evidence justifies a later
  persistence feature.

## Non-Goals

- Deleting, merging, rewriting, archiving, or physically compacting canonical
  proposal history.
- Replacing append-only proposal decision ledgers.
- Treating proposal acceptance as evidence that downstream implementation was
  completed or that the project will be implemented.
- Automatically deciding conflicts, validating assumptions, answering owner
  questions, or assigning heuristic coverage as owner-confirmed evidence.
- Generating or incrementally editing authoritative prose with an LLM.
- Making rendered publication or project narrative a readiness authority.
- Changing proposal, Change Set, Work, publication, or owner-governance
  lifecycle semantics.
- Introducing SQLite, PostgreSQL, a graph database, a daemon, a queue, a remote
  service, or a hosted cache in this feature.
- Making correctness depend on process-local cache survival.
- Requiring a workspace schema migration solely because a rebuildable derived
  read model is initially absent.
- Hiding stale, missing, partial, or failed derived state.

## Public Surface

The feature preserves existing command names and structured fields unless an
additive field is explicitly required below.

Expected command behavior:

| Surface | Required behavior |
| --- | --- |
| `p2p status` | fast summary; no implicit deep validation or complete freshness build |
| `p2p proposal list` | fast current lifecycle summaries with canonical fallback when a read model is stale |
| `p2p project progress` | batch, vertical-aware progress without repeated pack resolution |
| `p2p context --budget small` | bounded computation and output; explicit validation/freshness scope |
| `p2p next` | reuse one read context and avoid rebuilding freshness or decision context |
| `p2p validate` | explicit deep structural and semantic validation |
| `p2p project freshness` | explicit complete derived-state analysis |
| `p2p registry refresh` | atomically refresh the registry bundle and its manifest |
| `p2p registry status` | verify registry generation without reconstructing complete semantic records |
| `p2p project refresh` | refresh existing project projections and vertical project memory through supported writes |
| `p2p project memory status` | show structured read-model state and reasons without writing |
| `p2p project memory show` | show a bounded aggregate or exact-section view with explicit history and pagination controls, without writing |

CLI structured output and MCP read output must expose equivalent state,
freshness, provenance, and diagnostics. Any MCP refresh tool remains an explicit
write-safe operation and must not be inferred from a read call.

## Block A - Read Performance Foundation

### Runtime And Measurement

- A-R001: DEVELOPMENT tests and benchmarks SHALL prove whether imports resolve
  to the current source tree or to an installed artifact.
- A-R002: SOURCE-tree benchmarks SHALL fail or stop with a diagnostic when the
  measured module does not resolve to the intended source checkout.
- A-R003: PERFORMANCE evidence SHALL record command, dataset, Python version,
  package source, cold or warm mode, process model, elapsed time, filesystem
  discovery passes, source reads, YAML parses, hashes, schema evaluations,
  ledger parses, vertical-pack loads, and peak memory where practical.
- A-R004: CI correctness gates SHALL prefer structural operation counts and
  complexity assertions over narrow wall-clock assertions.

### Request-Scoped Read Context

- A-R005: EACH public composite read SHALL execute through one typed
  `WorkspaceReadContext` or an equivalent explicit request abstraction.
- A-R006: THE read context SHALL expose lazy providers. Constructing the context
  SHALL NOT eagerly build schema findings, lifecycle maps, vertical packs,
  registries, decision context, readiness, progress, freshness, or next actions.
- A-R007: EACH provider SHALL compute at most once per read context and SHALL
  return an immutable value or an immutable view.
- A-R008: CAPTURED source bytes SHALL be reused by hashing and parsing within the
  request. A selected path SHALL NOT be reopened by multiple consumers when the
  same captured representation is sufficient.
- A-R009: PARSED YAML SHALL be cached by path, captured physical hash, and loader
  contract. A specialized duplicate-key or domain codec SHALL NOT silently reuse
  a parse produced with weaker semantics.
- A-R010: THE context SHALL capture directory-discovery results used by the
  request and SHALL detect source additions, removals, or changes that occur
  before result publication.
- A-R011: ON concurrent source drift, a read SHALL retry from a fresh context at
  most once or return an explicit concurrent-change diagnostic. It SHALL NOT
  return a mixed-revision result as current.
- A-R012: READ contexts SHALL be request-scoped for CLI and MCP. Process-local
  service instances MAY be reused, but request data SHALL NOT survive into a
  later request without a source-identity key.
- A-R013: PUBLIC facades SHALL retain compatibility wrappers that create a read
  context when callers do not supply one.

### Schema And Lifecycle

- A-R014: WORKSPACE schema identity, compatibility, migration recovery, and
  complete layout validation SHALL be separate operations.
- A-R015: A targeted proposal lifecycle read SHALL inspect cheap schema preflight
  data and the target proposal ledger; it SHALL NOT validate every proposal
  ledger.
- A-R016: LIFECYCLE aggregation SHALL use one batch implementation that receives
  one schema preflight and parses each selected ledger at most once.
- A-R017: THE single-proposal lifecycle API SHALL delegate to the batch engine or
  the same private evaluator so single and batch semantics cannot diverge.
- A-R018: COMPLETE workspace validation MAY validate every ledger once. No deep
  schema, lifecycle, registry, status, context, readiness, or progress path MAY
  cause proposal-count-squared ledger parsing.
- A-R019: LIFECYCLE outputs, diagnostics, effective authority, proposal binding,
  lineage, and schema-v2 read compatibility SHALL remain unchanged.

### Vertical Batch Processing

- A-R020: ACTIVE vertical state and each resolved vertical pack SHALL be loaded
  at most once per read context.
- A-R021: DECLARED vertical coverage SHALL be evaluated through one batch engine
  over selected proposals.
- A-R022: COVERAGE validation SHALL precompute valid section IDs and SHALL NOT
  reload or revalidate the pack for each proposal.
- A-R023: HEURISTIC matching SHALL precompute section terms, frequencies, and
  regular expressions once per vertical pack and process proposal sources in a
  batch.
- A-R024: ORDINARY progress SHALL distinguish declared evidence from heuristic
  suggestions and SHALL be able to compute authoritative axes without requiring
  heuristic matching.
- A-R025: CALLERS that require heuristic detail SHALL request it explicitly or
  consume a current derived result; omission SHALL be represented explicitly,
  not as an authoritative empty set.

### Fast And Deep Paths

- A-R026: EVERY public read SHALL have an explicit cost class: fast, targeted,
  or deep.
- A-R027: `p2p status` SHALL NOT invoke complete validation, complete derived
  freshness, publication fingerprint reconstruction, or heuristic coverage.
- A-R028: `p2p proposal list` SHALL NOT invoke complete workspace layout
  validation once per proposal.
- A-R029: `p2p context --budget small` SHALL NOT invoke complete validation or
  complete freshness. Its output SHALL state whether validation and freshness
  are `not_run`, `fast_checked`, `current`, `stale`, `missing`, or `unknown`.
- A-R030: AN untargeted small context SHALL NOT build the full decision-context
  index solely to reproduce data already available in current vertical memory
  or registries.
- A-R031: A proposal-targeted context MAY build or consume the decision-context
  index because nearby retrieval is part of its requested behavior.
- A-R032: `p2p next` SHALL use the caller's read context and SHALL NOT independently
  rebuild decision context, freshness, lifecycle maps, proposal summaries, or
  readiness already present in that context.
- A-R033: `p2p project progress` SHALL reuse one proposal and vertical snapshot.
- A-R034: `p2p validate` and `p2p project freshness` SHALL remain explicit deep
  paths and SHALL share captured sources when executed inside one composite deep
  operation.
- A-R035: FAST status SHALL NOT claim that deep validation passed when it was not
  run.

### Registry Read Model

- A-R036: THE registry bundle SHALL have a versioned manifest that records
  generator contract version, source catalog policy version, source fingerprint,
  output digests, record counts, and owned output paths.
- A-R037: REGISTRY source fingerprinting SHALL identify same-count semantic
  source changes and SHALL exclude observation time, absolute root, and mtime
  from semantic identity.
- A-R038: PATH, size, and mtime MAY be used as a quick candidate-change filter,
  but content hash SHALL remain the reliable source identity.
- A-R039: REGISTRY refresh SHALL commit every registry file and the manifest as
  one recoverable atomic generation. Readers SHALL never accept a mixed
  generation as current.
- A-R040: REGISTRY status SHALL compare current source identity and the stored
  manifest without reconstructing complete proposal and Change Set semantic
  records.
- A-R041: A current registry MAY serve ordinary list and summary queries. A
  stale, missing, invalid, or unsupported registry SHALL trigger a canonical
  in-memory batch fallback or an explicit unavailable result.
- A-R042: A read-only fallback SHALL perform zero persistent writes. It MAY
  recommend the existing refresh command.
- A-R043: GENERATED registry records SHALL retain current public fields and
  deterministic ordering.

### YAML And Deep Validation

- A-R044: YAML parsing SHALL be routed through shared foundation helpers where
  semantics permit, with `CSafeLoader` used when available and a safe Python
  fallback otherwise.
- A-R045: SPECIALIZED unique-key loaders SHALL preserve duplicate-key rejection
  under both accelerated and fallback implementations.
- A-R046: COMPLETE validation SHALL reuse captured bytes and parsed forms rather
  than reopening every YAML independently for generic and specialized checks.
- A-R047: A parser optimization SHALL be accepted only after semantic parity,
  malformed-input, Unicode, merge-key, anchor, duplicate-key, and supported
  Python-version tests pass.
- A-R048: ALL Block A reads SHALL remain side-effect free and byte-invariant.

## Block B - Vertical Project-Memory Projection

### Artifact And Authority Contract

- B-R001: VERTICAL project memory SHALL be a derived, non-canonical read model
  rooted at `.p2p/project/vertical-memory/`.
- B-R002: THE owned output set SHALL contain exactly:
  `manifest.yml`, `project.yml`, and `sections/<section-id>.yml` for every active
  vertical section. Additional files require a versioned contract change.
- B-R003: THE manifest SHALL identify active vertical ID and version, vertical
  checksum, generator and policy versions, source fingerprint, per-scope source
  fingerprints, section output digests, owned paths, and generation mode.
- B-R004: VERTICAL memory SHALL be fully rebuildable from cataloged authority
  sources: canonical project definition, schema-v3 proposal decision events or
  schema-v2 compatibility sources selected by lifecycle policy, declared
  coverage, project questions, explicit relations, choices, conflicts, and
  source evidence used by decision context.
- B-R005: VERTICAL memory SHALL NOT become proposal, decision, definition,
  coverage, question, conflict, or governance authority.
- B-R006: ACTIVE decision contributions SHALL be selected from current lifecycle
  authority and current proposal binding. A proposal Markdown status alone SHALL
  NOT override schema-v3 decision authority.
- B-R007: ACCEPTANCE SHALL mean active project intent only. It SHALL NOT imply
  implementation, deployment, completion, publication, or commercial use.
- B-R008: REVOKED, rejected, withdrawn, deferred, superseded, split, merged, and
  replaced material SHALL retain historical traceability but SHALL NOT appear as
  an active project direction unless current lifecycle semantics explicitly make
  it active.

### Section Model

- B-R009: EACH section record SHALL include section identity, required status,
  priority, definition state, active decision contributions, historical
  contributions, explicit constraints, rationale evidence, assumptions, open
  questions, blockers, conflicts, declared evidence, heuristic suggestions,
  diagnostics, and source references when applicable.
- B-R010: EACH contribution SHALL retain proposal ID, current head event ID,
  authority and activation, contribution kind, source fragment or artifact,
  source digest, and applicable lineage.
- B-R011: ONE proposal MAY contribute to multiple declared sections without
  duplicating source authority or changing decision identity.
- B-R012: ONLY declared coverage SHALL place a proposal contribution into the
  authoritative section evidence set.
- B-R013: HEURISTIC coverage SHALL remain advisory, separately labeled, and
  excluded from authoritative evidence and readiness numerators.
- B-R014: ACTIVE proposals without valid declared coverage SHALL appear in an
  aggregate unmapped set with diagnostics and bounded retrieval metadata. They
  SHALL NOT be assigned silently to a section.
- B-R015: EXPLICIT conflict, winner, rejected direction, supersession, split,
  merge, revocation, and reinstatement evidence SHALL be represented without
  inventing a resolution.
- B-R016: WHEN active contributions appear contradictory and no explicit
  resolution exists, the section SHALL report an unresolved diagnostic and
  SHALL NOT choose a winner.
- B-R017: THE section model SHALL be structured. A generated prose summary MAY
  be rendered from it, but free-form prose SHALL NOT be the only stored form of
  a material fact.

### Full And Incremental Generation

- B-R018: A pure full builder SHALL render the complete candidate output set
  without writing files.
- B-R019: A pure impact classifier SHALL map changed canonical paths and typed
  decision operations to affected source scopes and vertical sections.
- B-R020: AN accepted, revoked, reinstated, superseded, split, or merged decision
  SHALL affect its declared sections, aggregate project state, and unmapped
  state as applicable.
- B-R021: A coverage change SHALL affect the proposal's previous and new
  sections. A vertical selection, pack checksum change, or section-contract
  change SHALL force a full rebuild.
- B-R022: A definition, assumption, blocker, or project-question change SHALL
  affect only its declared section when identity is exact; ambiguous or global
  changes SHALL force a safe broader rebuild.
- B-R023: AN incremental builder SHALL receive the current valid manifest and
  unchanged section records, render affected records, and produce a complete
  candidate generation.
- B-R024: FOR identical canonical sources, incremental output SHALL be
  semantically and byte equivalent to full rebuild output, excluding only fields
  explicitly documented as non-semantic. The preferred contract is complete
  byte equivalence.
- B-R025: GENERATION SHALL be deterministic under reversed source enumeration,
  repeated execution, process restart, and equivalent path ordering.
- B-R026: GENERATED output SHALL be committed atomically as one owned set. A
  failed commit SHALL leave the prior complete generation unchanged or enter the
  existing recoverable transaction state.
- B-R027: STALE section files from a previous vertical or contract SHALL be
  removed only through the owned-path manifest and the same atomic transaction.
- B-R028: REFRESHING a current generation SHALL be byte-idempotent.

### Refresh And Read Behavior

- B-R029: READ commands SHALL never refresh vertical memory implicitly.
- B-R030: `p2p project refresh` SHALL be the supported persistent refresh
  operation and SHALL include vertical-memory generation after preflight.
- B-R031: A successful governed source mutation MAY invoke a separate
  post-commit incremental derived refresh. Failure of that derived refresh SHALL
  NOT roll back or reinterpret the canonical mutation.
- B-R032: POST-COMMIT refresh result SHALL be reported as `updated`, `unchanged`,
  `stale`, `failed`, or `not_applicable` with affected sections and a suggested
  explicit refresh command.
- B-R033: EXTERNAL edits, Git changes, unsupported writes, or failed post-commit
  refresh SHALL be detected by source fingerprint on status or the next
  applicable read.
- B-R034: VERTICAL-memory status SHALL distinguish `current`, `stale`, `missing`,
  `invalid`, and `unsupported`. A refresh operation MAY additionally return
  `failed` without overwriting the last successful generation.
- B-R035: A stale read MAY show last-known data only when the payload is clearly
  labeled stale. A consumer that guides governance or readiness SHALL instead
  rebuild in memory from canonical sources or fail explicitly.
- B-R036: A missing or invalid read model SHALL never cause invented project
  state. Canonical in-memory fallback or an explicit unavailable result is
  required.
- B-R037: VERTICAL memory SHALL integrate with the derived-freshness dependency
  graph as a derived node and SHALL not be enumerated as a canonical source.
- B-R038: MATERIALIZED contribution records SHALL contain the smallest exact
  source fragment needed to preserve the fact and its rationale, plus source
  identity and digest. They SHALL NOT copy complete proposal or artifact bodies
  merely for convenience.
- B-R039: SECTION and aggregate records SHALL NOT embed decision-index postings,
  computed readiness gaps, next actions, rendered publication prose, or other
  independently derivable payloads. A compact contribution MAY appear in every
  explicitly declared applicable section, but it SHALL retain one stable
  authority identity and section-specific applicability.
- B-R040: PUBLIC list-bearing memory reads SHALL be bounded by default and SHALL
  return total, returned, truncation, and stable-cursor metadata. Complete
  historical material SHALL require an explicit option or paged traversal.
- B-R041: A post-commit derived update SHALL perform only a no-op or an
  incremental update against a current compatible generation. Missing,
  invalid, unsupported, or full-rebuild-required state SHALL be reported as
  `stale` or `not_applicable` with `p2p project refresh`; it SHALL NOT hide a
  full workspace rebuild inside the canonical mutation.
- B-R042: A registry, decision-context index, or other derived artifact MAY
  accelerate vertical-memory generation only when its contract and source
  fingerprint match the captured authority sources. Otherwise the builder SHALL
  rebuild the needed view in memory or fail explicitly; a derived artifact
  SHALL NOT add, suppress, or activate a material fact.

## Block C - Readiness, Retrieval, Next Actions, And Rendering

### Readiness

- C-R001: PROJECT readiness SHALL consume a current vertical-memory snapshot or
  a semantically equivalent canonical in-memory candidate.
- C-R002: READINESS classification policy and gap identities SHALL remain
  separate from vertical-memory generation to avoid a dependency cycle.
- C-R003: DEFINITION completeness SHALL continue to derive from explicit
  section status, required fields, assumptions, blockers, and project questions.
- C-R004: DECLARED evidence coverage SHALL continue to count only active
  owner-confirmed proposal coverage.
- C-R005: DEFINITION completeness and declared evidence coverage SHALL remain
  independent axes. No aggregate percentage SHALL replace them as authority.
- C-R006: HEURISTIC suggestions, rendered summaries, and publication prose SHALL
  not satisfy readiness evidence.
- C-R007: READINESS SHALL surface unresolved active conflicts, missing section
  mapping, stale authority, invalid projection, and failed fallback as explicit
  diagnostics or gaps according to policy.
- C-R008: AN incremental readiness update SHALL be semantically equivalent to a
  full classification from the same vertical-memory candidate.
- C-R009: INFORMATIONAL unmapped legacy detail SHALL remain bounded and paged;
  it SHALL NOT dominate ordinary readiness payloads or next actions.

### Context And Retrieval

- C-R010: AN untargeted small context SHALL use current vertical memory as its
  primary project-shape source.
- C-R011: A targeted context SHALL use vertical memory for section framing and
  the decision-context index for bounded nearby evidence.
- C-R012: RETRIEVAL SHALL prefer active current-direction evidence while
  preserving explicit access to relevant historical, conflicting, revoked, or
  superseded evidence when policy permits.
- C-R013: CONTEXT payloads SHALL preserve proposal, event, section, source, and
  fingerprint traceability for material claims.
- C-R014: CONTEXT SHALL state whether vertical memory, readiness, validation, and
  freshness were current, fast-checked, stale, missing, rebuilt in memory, or
  not run.
- C-R015: A context budget SHALL bound computation as well as serialized output.
  A small budget SHALL not trigger optional global heuristics or publication
  analysis.

### Next Actions

- C-R016: NEXT actions SHALL consume the same request context used by the caller.
- C-R017: PROJECT readiness actions SHALL be derived from current structured
  gaps, not from rendered prose.
- C-R018: DECISION-remediation actions SHALL use current lifecycle and impact
  snapshots without rebuilding full freshness per decision.
- C-R019: STALE or invalid vertical memory SHALL produce at most one stable,
  explainable refresh or repair action before section-level actions that depend
  on it.
- C-R020: NEXT action identity and ordering SHALL remain deterministic across
  repeated reads and unrelated proposal additions.

### Project Rendering

- C-R021: EXISTING project projection and visible export workflows SHALL render
  a vertical-first current-project structure instead of a chronological proposal
  dump when current vertical memory is available.
- C-R022: RENDERED output SHALL distinguish current direction, historical
  context, pending owner decision, risk, assumption, blocker, missing evidence,
  and legacy unmapped material.
- C-R023: RENDERING SHALL retain compact source references for material claims.
- C-R024: RENDERED output SHALL remain derived and SHALL NOT change proposal,
  decision, readiness, publication-review, Change Set, or Work authority.
- C-R025: A stale or unavailable vertical-memory projection SHALL be disclosed;
  rendering SHALL use a canonical in-memory candidate or stop rather than
  silently publishing stale project state as current.

## Block X - Persistence Decision

- X-R001: BLOCK X SHALL execute only after Blocks A, B, and C pass their source,
  fixture, and read-only or scratch-current-repository gates. Persistent
  current-repository alignment belongs to Block M and is not a prerequisite for
  the persistence decision.
- X-R002: MEASUREMENTS SHALL cover at least current-project scale, a deterministic
  1,000-proposal fixture, and a 10,000-proposal structural-complexity fixture.
- X-R003: CLI measurements SHALL distinguish cold process with empty process
  cache from repeated separate CLI invocations.
- X-R004: MCP measurements SHALL distinguish first request, warm request,
  post-mutation request, and concurrent read/write behavior.
- X-R005: THE evaluation SHALL measure source discovery, parsing, hash work,
  projection load, full rebuild, incremental rebuild, context retrieval, peak
  memory, and artifact size.
- X-R006: THE evaluation SHALL end with exactly one recorded outcome:
  `filesystem_sufficient` or `persistent_index_feature_required`.
- X-R007: `filesystem_sufficient` SHALL be selected when the targets and
  complexity gates pass without correctness depending on process-local cache.
- X-R008: `persistent_index_feature_required` SHALL identify the measured
  bottleneck, affected commands, invalidation requirements, recovery contract,
  migration impact, and expected benefit for a separate future proposal or
  feature.
- X-R009: BLOCK X SHALL NOT add SQLite, a database dependency, a cache directory,
  a cache migration, a cleanup command, or cache-dependent correctness.

## Non-Functional Requirements

- N001: ALL ordering, identities, fingerprints, diagnostics, and generated
  outputs SHALL be deterministic.
- N002: ALL read operations SHALL be byte-invariant across canonical and derived
  workspace state.
- N003: DERIVED state SHALL be replaceable, rebuildable, and non-authoritative.
- N004: NO fast read SHALL silently weaken governance or lifecycle authority.
- N005: NO write correctness check SHALL rely only on mtime, size, a process
  cache, or a previously returned read model.
- N006: ROOT-relative paths SHALL be used in public payloads and fingerprints;
  absolute checkout paths SHALL not affect semantic identity.
- N007: GENERATED writes SHALL use existing safe-path, precondition, lock,
  transaction, rollback, and recovery primitives.
- N008: CLI and MCP read payloads SHALL remain JSON-ready and schema-versioned.
- N009: PUBLIC additive fields SHALL have stable names, documented states, and
  compatibility tests.
- N010: IMPLEMENTATION SHALL support Python 3.11 and every newer Python version
  declared by project tooling.
- N011: OPTIONAL C-accelerated YAML support SHALL not become an undeclared hard
  dependency.
- N012: FAST paths SHALL remain useful when registries or vertical memory are
  absent by using bounded canonical fallback.
- N013: A current-project fast read SHALL target these reference ceilings on the
  documented development machine with a cold Python process and warm filesystem
  cache: `status < 1.0 s`, `proposal list < 1.0 s`, `registry status < 1.0 s`,
  `project progress < 2.0 s`, untargeted `context small < 2.0 s`, targeted
  `context small < 3.0 s`, and `next --top 3 < 2.0 s`.
- N014: DEEP current-project reference targets SHALL be documented separately;
  the initial goals are `validate < 5.0 s` and `project freshness < 5.0 s`
  without repeated global construction.
- N015: CI SHALL enforce no proposal-count-squared behavior and bounded
  structural growth from 100 to 1,000 to 10,000 proposals. The 10,000-proposal
  fixture need not satisfy the current-project subsecond wall-clock targets.
- N016: PERFORMANCE targets SHALL record median and at least one high percentile
  outside flaky correctness tests. CI wall-clock limits SHALL include reasonable
  platform tolerance.
- N017: PEAK memory and output size SHALL grow linearly or better with selected
  source count, excluding explicitly bounded index postings.
- N018: NO network access, model call, embedding service, locale-dependent
  analyzer, or wall-clock date SHALL be required for deterministic project
  memory.

## Error And Recovery Requirements

- E001: A concurrent source mutation SHALL produce a retry or explicit
  concurrent-change result, never a mixed snapshot.
- E002: A malformed selected ledger SHALL affect only its lifecycle record and
  the aggregate completeness required by existing policy; it SHALL not trigger
  repeated global parsing.
- E003: A malformed vertical pack, definition, coverage, or section record SHALL
  produce a stable path-specific diagnostic.
- E004: A stale registry SHALL never suppress a newer canonical decision.
- E005: A mixed or partially written registry generation SHALL be rejected.
- E006: A failed registry or vertical-memory atomic refresh SHALL preserve the
  previous complete generation or enter recoverable transaction state.
- E007: A vertical-memory source fingerprint mismatch SHALL report changed
  scopes or paths where available.
- E008: A missing declared section target SHALL quarantine the affected
  contribution and report a diagnostic; it SHALL not create a synthetic section.
- E009: An unresolved conflict SHALL remain unresolved in memory, readiness, and
  rendering.
- E010: A post-commit derived refresh failure SHALL not roll back a successful
  canonical governance mutation.
- E011: A canonical fallback failure SHALL stop authority-sensitive consumers
  and include the command needed to validate or refresh state.
- E012: Unsupported read-model contract versions SHALL be reported as
  `unsupported`, not parsed best-effort as current.

## Acceptance Criteria

- AC001: Source import provenance is checked and all performance evidence names
  the actual measured source or installed artifact.
- AC002: One read context loads each requested schema preflight, lifecycle map,
  vertical pack, registry view, decision index, readiness result, progress
  result, freshness result, and next-action result at most once.
- AC003: Proposal aggregation parses at most one ledger per selected proposal
  and performs no full layout validation inside the proposal loop.
- AC004: Reversing 100, 1,000, and 10,000 proposal enumeration does not change
  lifecycle, progress, readiness, memory, context, or next-action semantics.
- AC005: Fast `status`, `proposal list`, `context small`, `next`, and `progress`
  do not invoke deep validation or complete freshness unexpectedly.
- AC006: Deep validation retains all existing findings and detects malformed
  generic and specialized YAML under accelerated and fallback loaders.
- AC007: Registry status detects same-count source changes and rejects a mixed
  generation.
- AC008: Registry and vertical-memory refresh failure injection proves atomicity,
  rollback, and recovery behavior.
- AC009: A full vertical-memory generation contains every active vertical
  section and no undeclared synthetic section.
- AC010: Active, revoked, reinstated, superseded, split, merged, rejected,
  deferred, draft, and unknown legacy decision states appear in the correct
  active, historical, or excluded role.
- AC011: Unmapped and heuristic proposal evidence is visible but excluded from
  authoritative section evidence and readiness numerators.
- AC012: Incremental generation is byte-equivalent to full generation for every
  supported impact class.
- AC013: A vertical switch removes stale owned section outputs atomically and
  rebuilds all sections.
- AC014: A canonical decision apply succeeds even when injected derived refresh
  fails, and the resulting stale memory is detected and remediable.
- AC015: Readiness retains separate definition and declared-evidence axes and
  produces equivalent results from current materialized memory and canonical
  in-memory fallback.
- AC016: Untargeted context uses vertical memory without full decision-index
  construction; targeted context retains bounded nearby decision retrieval.
- AC017: Next actions reuse the caller context and produce stable identities and
  ordering after unrelated proposal additions.
- AC018: Project rendering is vertical-first, traceable, state-aware, and never
  treated as governance or readiness authority.
- AC019: All read-only operations leave the repository byte-for-byte unchanged.
- AC020: Current-project fast and deep measurements meet N013-N014 or document a
  failing exit gate that blocks downstream blocks.
- AC021: Public CLI, MCP, docs, generated agent templates, package contents,
  Python 3.11 checks, focused suites, and full suites pass.
- AC022: Block X records one evidence-backed persistence outcome and introduces
  no database or persistent cache implementation.
- AC023: A large proposal mapped to multiple sections stores only material
  fragments and references, public memory/context reads remain bounded, and
  projection size remains linear without duplicating complete source artifacts.
- AC024: A successful canonical mutation that requires a full projection rebuild
  returns canonical success plus a stale/not-applicable derived result and does
  not perform the full rebuild implicitly.
- AC025: Stale, missing, invalid, and unsupported accelerator artifacts produce
  the same vertical-memory semantics through canonical fallback or an explicit
  unavailable result; they never alter active authority or material facts.

## Delivery Constraints

- Block A is required before Block B implementation begins, except for isolated
  contract drafting and pure fixtures.
- Block B must pass full-versus-incremental equivalence before Block C consumers
  switch to materialized vertical memory.
- Block C consumers must retain canonical in-memory fallback until Block X is
  complete.
- Requirement-to-design-to-task-to-test traceability must be updated after every
  slice, not reconstructed only at the final gate.
- Implementation may refine reference timings after recording reproducible
  baseline conditions, but may not remove structural complexity gates.
- Local wheel/sdist builds and isolated installs are verification only. This
  feature does not authorize a commit, tag, push, release, package upload, or
  remote publication.
