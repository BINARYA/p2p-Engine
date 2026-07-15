# Implementation Evidence - PROP-100 Decision Context Index

## Authorization

- `PROP-100` was accepted by the owner before implementation started.
- Implementation is repository work under `src/`, `tests/`, `docs/` and this
  feature directory. No implementation task writes canonical `.p2p/` state.

## Baseline - 2026-07-15

Measured on the current project with P2P Engine `0.1.9`:

| Command | Elapsed |
| --- | ---: |
| `p2p context --target PROP-100 --budget small` | 57.80 s |
| `p2p context --budget small` | 56.69 s |

The shared latency before target-specific rendering shows that the dominant cost
is global context construction. The current call path invokes validation,
registry status, project state, proposal summaries, choice statuses, Change Set
statuses, Work summaries and next actions. `RegistryRecordBuilderService` also
calls `changes_for_proposal()` from proposal-record construction, and that helper
rebuilds all Change Set records for each proposal.

Structural performance gates for this feature:

- one decision-context source discovery pass per index build;
- at most one read/hash/parse for each selected source;
- no registry projection as semantic input;
- no per-proposal full Change Set reconstruction;
- zero source reads after index construction;
- representative fixture build plus one query under five seconds.

## Source Classification Matrix

| Source family | Current reader/service | Classification |
| --- | --- | --- |
| Proposal body | `ProposalDocumentService` | canonical semantic source |
| Proposal decision | `ProposalDecisionService` / proposal readers | canonical semantic source |
| Related, impact, conflict artifacts | `ProposalArtifactService` | governed artifact evidence |
| Artifact state/readiness | dedicated proposal services | quality metadata |
| Questions/contributions | dedicated proposal services | advisory/applied-state evidence |
| Project choices and links | `ChoiceLifecycleService` | canonical semantic source |
| Project conflicts | `ConflictMemoryService` | canonical semantic source |
| Change Set source/link files | `ChangeSetLifecycleService` | canonical semantic source |
| Work manifests | `WorkPlanningService` | execution-state metadata |
| Vertical coverage | `ProjectVerticalService` | declared relation or heuristic signal |
| Decision precedents/governance | `GovernanceService` / policy service | bounded project context |
| Project definition | `ProjectVerticalService` | bounded project context |
| Registries/decision maps | registry/project-state services | derived projection, excluded |
| Briefs/prompts/publications/exports | renderer/publication services | generated output, excluded |
| Future decision-context cache | none | derived infrastructure, excluded |

## Consumer Compatibility Matrix

| Consumer | Current contract to preserve during initial slices |
| --- | --- |
| `ContextPacketService` | legacy fields and target validation |
| CLI text context | current headings, commands and non-proposal behavior |
| CLI YAML context | generic JSON/YAML-ready dataclass serialization |
| MCP `p2p_context` | current input schema and JSON-ready output fields |
| Intake context | controlled apply remains separate from prompt evidence |
| Proposal prompts | existing prompt commands and import contracts |
| Next actions | action priority and project-choice semantics |
| Registries | derived file formats remain legacy projections |

The first public nearby-context integration supports `PROP-*` only. `CHANGE-*`,
`CHOICE-*`, `WORK-*` and no-target behavior remain unchanged.

## Validation Commands

Focused commands are recorded alongside each slice. The stable command groups
are:

```text
.venv/bin/pytest tests/test_decision_context_sources.py tests/test_decision_context_service.py
.venv/bin/pytest tests/test_decision_context_authority.py tests/test_decision_context_topology.py
.venv/bin/pytest tests/test_decision_context_retrieval_service.py
.venv/bin/pytest tests/test_decision_context_performance.py
.venv/bin/pytest tests/test_context_packet_service.py tests/test_mcp.py -k context
.venv/bin/pytest tests/test_project_context_renderer_service.py tests/test_intake_lifecycle_service.py tests/test_proposal_artifact_service.py
.venv/bin/pytest tests/test_next_actions_service.py tests/test_registry_record_builder_service.py tests/test_registry_service.py
.venv/bin/pytest tests/test_decision_context_freshness.py
./scripts/test-public.sh
./scripts/test-smoke.sh
./scripts/test-full.sh
```

## Slice Evidence

### Slice A - Domain, Sources And Proposal Decisions

- Added typed/versioned domain contracts and JSON-ready serialization.
- Added deterministic proposal/decision Source Catalog and request snapshot.
- Added captured-byte Markdown/frontmatter parsing with spans and diagnostics.
- Added stable semantic-slot IDs and separate content/source hashes.
- Added proposal claims and complete decision lifecycle extraction.
- Added stateless `ProjectDecisionContextService` behind `P2PWorkspace`.
- Proved one discovery/read/hash/parse, same-workspace freshness and no writes.

Validation:

```text
25 passed in 0.30s
15 existing proposal/context/workspace regressions passed in 1.36s
```

### Slice B - Authority And Topology

- Expanded the source catalog to proposal artifacts, project choices, Change
  Sets, Work, project conflicts, vertical coverage and bounded governance/project
  definition sources while excluding registries and generated output.
- Added separate canonicality, authority, activation, confidence and
  completeness handling, including artifact confirmation resolution.
- Added typed identity/value nodes, controlled relation aliases, deterministic
  symmetric/directed identities and evidence-preserving edge merge.
- Normalized Change Set lineage, Work execution, related proposals, impacts,
  conflicts, choices, vertical coverage and quality/event metadata.
- Added bounded governance constraints and explicit precedent applicability for
  proposal, choice and tag references.
- Added quarantine diagnostics for missing/self/unsupported relations, divergent
  Change Set links and incompatible active lineage assertions.
- Proved cycle/fan-out termination, one source read/hash/parse and deterministic
  relation/evidence output.

Validation:

```text
45 focused decision-context tests passed in 0.42s
59 focused plus existing proposal/context/workspace regressions passed in 1.61s
Real workspace: 1,353 sources, 2,170 records, 531 nodes, 578 relations,
2,810 evidence entries, max one read per source; partial with 30 historical
source/topology diagnostics.
```

### Slice C - Explainable Retrieval And Budgets

- Added fixed NFKC/casefold lexical normalization, bilingual stop words, domain
  preservation for IDs/commands/paths and corpus-based ubiquitous-term handling.
- Added immutable lexical/domain postings and owner authority/activation indexes.
- Added proposal-target and idea-text candidate construction with a 200-owner
  cap, explicit applicability, domain/vertical matches and one bounded medium
  traversal hop.
- Added versioned score arithmetic, authority/lifecycle eligibility, historical
  threshold, stable tie-breaking and one hit per owner with usable content.
- Added exact small/medium hit, record, relation, reason and compact JSON UTF-8
  byte budgets with deterministic truncation metadata.
- Preserved score explainability under reason limits by deterministic aggregate
  reasons; empty queries return `DC-RETRIEVAL-EMPTY` with no first-N fallback.
- Added heuristic vertical matching strictly as a retrieval reason, never as a
  topology edge.

Validation:

```text
61 Slice A/B/C decision-context tests passed in 0.39s
15 existing context/proposal/workspace regressions passed in 0.66s
Real PROP-100 build: 0.545s; query: 0.071s; small packet: 11,105 bytes;
max one source read; relevant hits PROP-099, PROP-086, PROP-096 and PROP-085.
```

### Slice D - Performance Remediation

- Replaced per-proposal full Change Set reconstruction with one operation-scoped
  Change Set build and a proposal lookup index.
- Reused one context-request snapshot across current-state counts, default
  artifacts, validation registry checks, project state and next actions.
- Preserved standalone public service behavior when no snapshot is supplied.
- Added call-count regressions and a deterministic 100-proposal, 25-Change Set,
  20-choice scale fixture with lifecycle diversity, local votes, conflicts,
  vertical coverage and malformed optional evidence.

Validation and before/after measurement:

```text
Legacy target context: 57.80s -> 2.37s
Legacy default context: 56.69s -> 2.34s
48 context/registry/next-action/validation/performance tests passed in 2.35s
Scale fixture: one discovery pass; max one read/hash/parse per selected source;
zero query reads; build plus query below the 5s gate.
```

### Slice E - Context Packet, CLI And MCP

- Added optional versioned `nearby_context` without removing or renaming any
  legacy context field.
- Enabled one decision-index build only after valid `PROP-*` target resolution;
  no-target, Change, Choice and Work contexts keep retrieval disabled.
- Added compact text output plus equivalent JSON-ready YAML, JSON and MCP
  structures, including empty/partial diagnostics and source fingerprints.
- Added medium non-goals/rationale support while keeping non-goals out of
  positive lexical candidate construction and small payloads.
- Replaced generic dataclass serialization at CLI/MCP boundaries with explicit
  enum, tuple and immutable-mapping handling.
- Documented target behavior, budgets, empty results and the no-cache boundary
  in the CLI and MCP guides.

Validation:

```text
12 context/CLI tests passed in 3.83s
1 focused MCP context test passed in 0.39s
236 public contract tests passed in 66.10s
Integrated real PROP-100 context: 4.93s including legacy validation/current
state plus decision index and retrieval.
```

### Slice F - Intake And Proposal Prompt Neighborhood

- Replaced intake proposal/change/decision/relation registry slices with one
  `medium` idea-text retrieval packet; status and overview remain independent
  non-semantic metadata.
- Added a compact phase renderer with evidence paths, authority, activation,
  policy/fingerprint metadata, bounded diagnostics and deterministic byte caps.
- Added exploration context for decisions, constraints, scope boundaries and
  historical alternatives.
- Added impact context for selected normalized conflicts, capabilities,
  surfaces, vertical sections and artifact authority. Heuristic vertical matches
  are labelled retrieval signals and are never emitted as edges.
- Added synthesis context for accepted or qualified decisions, decided project
  choices, binding constraints and historical alternatives without changing
  owner-controlled decisions.
- Removed `decisions-map.yml` and full project conflict contents from migrated
  prompt semantics. Existing prompt and intake CLI/MCP result shapes are
  unchanged.
- Proved prompt generation changes only generated intake/prompt paths; no
  contribution, choice, relation, proposal artifact or decision writeback occurs.

Validation:

```text
41 intake/context/proposal-artifact/CLI/MCP focused tests passed in 4.48s
Relevant idea selected PROP-031 beyond the former first-30 boundary.
Generic ideas returned explicit empty context; all phase neighborhoods stayed
within the 40,000-byte medium policy limit.
```

### Slice G - Next Actions And Legacy Registry Projections

- Normalized active choice blocks from canonical `links.yml` into typed
  `CHOICE --blocks--> PROPOSAL|CHANGE` relations; invalid targets emit
  diagnostics and no edge.
- Fixed open choice placeholders so `Pending.` decision files are not treated as
  decided project choices.
- Migrated generated choice actions from mixed `choice_records()` projections to
  normalized project-choice nodes, decided-choice records and active block
  relations. Proposal-local votes no longer produce `resolve_choice` actions.
- Kept Change Set lifecycle status in its existing reader while resolving
  included-proposal context from active typed `includes` relations.
- Reused a single operation-scoped decision index between context next actions
  and proposal nearby retrieval; invalid targets still fail before index build.
- Kept `relations.yml` byte/schema behavior unchanged as a legacy derived
  projection. The source catalog excludes it and no normalized public relation
  registry or durable diagnostic artifact was added.

Validation:

```text
53 next-action/topology/context/performance/registry tests passed in 3.24s
10 focused CLI/MCP next-action tests passed in 3.51s
Covered open/decided choices, proposal-local votes, missing targets, active
blockers, historical conflicts, normalized Change Set links and no-action state.
```

### Slice H - Freshness And In-Memory Manifest Contract

- Kept source fingerprints based on catalog version plus sorted expected path,
  presence and captured-byte hash entries; same-size edits and source
  creation/deletion invalidate freshness.
- Centralized semantic fingerprint construction over source fingerprint and
  extractor, authority and relation policy versions.
- Added packet semantic fingerprinting that includes retrieval and budget policy
  versions.
- Added an injected-clock manifest builder with schema/generator/policy versions,
  source and semantic fingerprints, generated time and sorted input metadata.
- Added semantic manifest comparison that deliberately excludes `generated_at`.
- Added actionable stale reasons for source add/remove/presence/hash changes and
  schema, generator, catalog, extractor, authority, relation, retrieval and
  budget version changes.
- Kept all freshness behavior in memory. Intake and prompt files are one-shot
  generated artifacts, not reusable materialized projections with a contracted
  manifest path, so no manifest write or atomic replacement path was introduced.

Validation:

```text
62 freshness/source/index/retrieval/context tests passed in 1.49s
16 public context renderer/CLI/MCP tests passed in 2.50s
Different injected clocks produced semantically equal manifests; freshness
build/check left the workspace byte-for-byte unchanged.
```

### Slice I - Cache Decision

Decision: `cache_deferred`.

Measurements include Python allocation tracing, so they are intentionally more
conservative than the untraced Slice C timings:

| Workspace | Build | Query | Peak | Sources | Records | Relations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Representative 100/25/20 fixture | 0.344 s | 0.003 s | 2.92 MB | 1,191 | 900 | 84 |
| Current project | 1.893 s | 0.203 s | 13.65 MB | 1,353 | 2,170 | 578 |

Both measurements used one discovery pass, at most one read/hash/parse per
source and no query reads. The representative build plus query remains well
below the five-second ceiling, and current-project memory/latency does not
justify persistence complexity.

PROP-100 therefore adds no cache path, lock, migration, cleanup command,
corruption recovery or cache-dependent correctness behavior. If future scale
crosses the measured gates, a separate feature must define those contracts
before implementing persistence.

## Final Validation And Acceptance Evidence

Final commands:

```text
75 decision-context unit/service tests passed in 0.49s
51 focused consumer/registry/MCP tests passed in 3.58s
236 public CLI/MCP tests passed in 70.37s
14 smoke tests passed in 0.54s
39 post-hardening intake/prompt/next-action/context tests passed in 4.61s
744 final full tests passed in 95.32s
p2p validate: 0 errors, 0 warnings, 0 infos
```

The final real command `p2p context --target PROP-100 --budget small` completed
in 4.90 seconds, compared with the 57.80-second pre-remediation target baseline.
The default pre-remediation baseline was 56.69 seconds; the legacy-only Slice D
path reached 2.37/2.34 seconds before nearby retrieval was integrated. The final
path includes validation, normalized next actions, one shared decision index and
bounded retrieval.

Acceptance evidence:

| Criterion | Direct evidence |
| --- | --- |
| AC001 | Source/index tests cover stable IDs, hashes, spans, authority, completeness and root-relative evidence. |
| AC002 | Source, retrieval and performance counters prove one discovery, one read/hash/parse and zero query reads. |
| AC003 | Source parser tests cover LF/CRLF, duplicate headings, fences, malformed YAML/frontmatter and missing sections. |
| AC004 | Authority/topology tests cover lifecycle outcomes, conditional decisions, divergence, choices, precedents and metadata authority. |
| AC005 | Topology tests cover all node/relation families, aliases, merged evidence, Change Set divergence, invalid targets, blocks and bounded traversal. |
| AC006 | Retrieval golden/adversarial tests cover score arithmetic, caps, tie-breaks, historical thresholds, empty results and byte budgets. |
| AC007 | Enumeration, repeated retrieval and freshness tests prove deterministic output plus source/policy invalidation. |
| AC008 | Same-workspace tests rebuild after canonical edits and return changed fingerprints/content. |
| AC009 | The 100-proposal/25-change/20-choice fixture completes build plus query in 0.347 seconds unambiguously below 5 seconds. |
| AC010 | Context service/CLI tests expose `small`/`medium` nearby context while preserving legacy fields. |
| AC011 | CLI text/JSON/YAML and MCP tests verify parity; non-proposal nearby context remains disabled. |
| AC012 | Intake/prompt tests select `PROP-031` beyond first-N, bound phase payloads and prove no controlled writeback. |
| AC013 | Next-action tests prove local votes never become project choices and decided/missing targets create no active resolution action. |
| AC014 | Freshness tests distinguish content, presence and every policy version while ignoring `generated_at` semantically. |
| AC015 | Source, context, freshness, intake and prompt before/after snapshots prove no index/cache/manifest writes. |

All AC001-AC015 are met. Repository status still contains canonical `.p2p/` and
publication changes produced before this implementation during PROP-100
acceptance/publication work. This implementation did not manually edit those
paths: its durable edits are limited to `src/`, `tests/`, `docs/`, `README.md`
and `specs/features/prop-100-decision-context-index/`. Source scans confirm that
registries, decision maps, generated narratives, prompts, publications and
caches are not read by decision-context extraction.
