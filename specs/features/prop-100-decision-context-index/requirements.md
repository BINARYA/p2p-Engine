# Requirements - PROP-100 Decision Context Index

## Scope

Implement the software improvement described by `PROP-100`: a derived,
non-canonical, rebuildable and explainable decision context layer that lets P2P
retrieve nearby decisions, constraints, relations, conflicts and proposal
neighborhoods without rereading every proposal artifact for every consumer.

This repository specification refines the implementation contract. It does not
accept, reject or otherwise decide `PROP-100` and it does not change canonical
P2P state.

## Origin And Delivery State

- Source P2P proposal: `PROP-100 - Project Decision Context Index and Proposal
  Neighborhood`.
- Proposal state captured when this feature was created: `draft`, decision
  `pending`.
- Local implementation state: specification only.
- Every implementation slice requires code and direct test or observed public
  behavior before its tasks can be marked complete.

## In Scope

- A read-only `ProjectDecisionContextService` facade backed by cohesive source,
  extraction, authority, topology, retrieval and freshness components.
- A request-scoped immutable source snapshot that reads, hashes and parses each
  selected source at most once.
- An explicit source catalog and inclusion, authority and exclusion matrix.
- Typed source documents, parsed fragments, records, nodes, relations, evidence,
  diagnostics, retrieval requests/hits/packets and manifests.
- Proposal and decision claim extraction, including the complete decision
  lifecycle and evidence chains between a decision and the proposal content it
  activates or makes historical.
- Decision precedents and a bounded subset of project-wide governance and
  project-definition constraints with explicit authority.
- Relation normalization across proposal artifacts, choices, conflicts, Change
  Sets, vertical coverage and execution-state links.
- Deterministic lexical and topology retrieval for proposal IDs and idea text.
- Versioned retrieval policies and exact `small` and `medium` nearby-context
  budgets.
- Gradual migration of context packets, intake, proposal prompts, next actions,
  registries/projections, CLI and MCP consumers.
- Source fingerprints and freshness metadata for materialized derived outputs.
- Profiling and removal of repeated scans that would make context integration
  operationally unsafe.
- Synthetic golden, adversarial, malformed-source, determinism, scale and public
  contract tests.

## Out Of Scope

- Replacing canonical Markdown or YAML sources under `.p2p/`.
- Writing decisions, relations, tags, constraints, proposal status or other
  governed state from the derived index.
- Using generated registries, project publications, summaries or prompts as
  semantic source material.
- Changing owner authority, proposal lifecycle, governance, Git collaboration,
  consent or controlled-apply behavior.
- Introducing SQLite, PostgreSQL or another persistent cache in the initial
  implementation.
- Embeddings, network search or a non-explainable ranking signal.
- Generic natural-language interpretation of every governance or project file.
  Only explicitly cataloged fields and sections are extracted.
- Redesigning vertical packs, governance runtime or Work lifecycle.
- Removing current registries or compatibility fields.

## Public Surface And Compatibility

- Initial domain, extraction and retrieval slices have no CLI or MCP changes.
- `p2p context` may later gain a versioned `nearby_context` field while keeping
  current required fields.
- The first integration applies nearby retrieval to `PROP-*` targets. Existing
  `CHANGE-*`, `CHOICE-*`, `WORK-*` and untargeted behavior remains unchanged
  until separately specified.
- CLI text, CLI structured output and MCP JSON payloads must expose equivalent
  semantics for any shared field. MCP input schemas need change only if inputs
  change; output payload shape is protected by contract tests.
- Intake and proposal prompts may consume the derived index, but retrieval never
  expands controlled apply or performs a governed mutation.
- Any persisted output is derived, disposable and rebuildable. The first release
  keeps the index in memory.

## Functional Requirements

### Boundary And Architecture

- R001: THE SYSTEM SHALL keep governed Markdown and YAML artifacts as canonical
  source of truth.
- R002: THE SYSTEM SHALL expose decision context through a read-only facade that
  performs no canonical or derived filesystem write while building or querying
  an in-memory index.
- R003: THE facade SHALL delegate source cataloging, source snapshots, parsing,
  extraction, authority resolution, relation normalization, retrieval and
  freshness to independently testable collaborators.
- R004: `P2PWorkspace` SHALL remain the compatibility facade and SHALL NOT make a
  memoized decision-context service retain a stale source snapshot across
  requests.

### Source Catalog And Extraction Session

- R005: THE SYSTEM SHALL create one immutable extraction session per index build
  with a deterministic source catalog, normalized root-relative paths, source
  presence state, source bytes, hashes, parsed fragments and diagnostics.
- R006: WITHIN one extraction session, THE SYSTEM SHALL discover the source set
  once and SHALL read, hash and parse each selected source at most once.
- R007: Hashing and parsing SHALL use the same captured bytes so that a file
  change during extraction cannot produce a hash/content mismatch.
- R008: THE source catalog SHALL classify every supported source kind as
  canonical semantic source, governed imported evidence, quality metadata,
  execution-state metadata, derived projection or excluded source.
- R009: THE source catalog SHALL explicitly exclude registries, decision maps,
  project overview/scope projections, generated operational briefs, generated
  prompts, publication outputs and decision-context caches from semantic
  extraction.
- R010: THE first extractor slice SHALL catalog and parse proposal and decision
  sources only. Later source kinds SHALL be added without changing first-slice
  record identity.

### Domain And Evidence Contracts

- R011: THE SYSTEM SHALL provide typed contracts for `SourceDocument`,
  `ParsedFragment`, `DecisionContextEvidence`, `DecisionContextRecord`,
  `DecisionContextNode`, `DecisionContextRelation`,
  `DecisionContextDiagnostic`, `DecisionContextIndex`, `RetrievalRequest`,
  `RetrievalPolicy`, `RetrievalHit`, `DecisionContextPacket` and
  `DecisionContextManifest` or equivalent types.
- R012: Every public or persisted structure SHALL have deterministic JSON-ready
  serialization and an explicit schema version.
- R013: Record identity SHALL derive from normalized source path, owner identity,
  record kind and semantic fragment anchor with occurrence index. Line numbers,
  filesystem order, file modification time and content hash SHALL NOT be part of
  record identity.
- R014: Fragment content hash SHALL be stored separately from stable identity so
  content changes are detectable without confusing identity and freshness.
- R015: Every evidence reference SHALL include root-relative source path, source
  hash, source kind, fragment ID, semantic label, optional line/span metadata,
  canonicality, authority, activation, confidence and completeness.
- R016: Index and source completeness SHALL use the explicit states `complete`,
  `partial` and `unavailable`; a boolean partial flag is insufficient.
- R017: Multiple list items or repeated sections SHALL receive deterministic
  occurrence identities and SHALL remain independently traceable.

### Parsing And Claim Extraction

- R018: Markdown parsing SHALL support LF and CRLF, optional spacing after
  headings, fenced code blocks, repeated headings, missing trailing newlines and
  legacy empty sections without treating heading-like text inside a code fence as
  a section.
- R019: Frontmatter parsing SHALL distinguish absent, empty and malformed YAML
  and SHALL emit diagnostics instead of silently converting malformed content to
  an empty mapping.
- R020: Proposal extraction SHALL use an explicit section-to-claim mapping for
  problem, goals, non-goals, proposal, acceptance criteria and proposal status.
- R021: Decision extraction SHALL represent status/outcome, reason, approver and
  decision date and SHALL link the decision evidence to proposal claims it
  activates, qualifies or makes historical.
- R022: THE decision lifecycle SHALL handle `accepted`,
  `accepted_with_changes`, `rejected`, `deferred`, `split`,
  `merged_into_other`, `superseded`, pending and unknown/legacy states.
- R023: `accepted_with_changes` SHALL retain the decision reason as a qualifying
  constraint and SHALL NOT activate the proposal body as if it were an
  unconditional acceptance.
- R024: A divergence between proposal status and decision outcome SHALL produce
  a diagnostic. Decision evidence controls decision authority for retrieval, but
  the index SHALL NOT repair either source.

### Authority And Source Semantics

- R025: Canonicality, authority, activation, confidence and completeness SHALL be
  separate fields; no field SHALL be inferred solely from another field at
  serialization time.
- R026: THE authority policy SHALL be declarative, versioned and independently
  testable.
- R027: THE authority policy SHALL distinguish accepted decisions, conditionally
  accepted decisions, decided project choices, explicit decision precedents,
  accepted proposal context, draft proposals, deferred/rejected/split/merged/
  superseded history, project-definition constraints, owner-confirmed evidence,
  system state, agent-proposed evidence, proposal-local votes, applied questions,
  unapplied answers and heuristic vertical signals.
- R028: Artifact confirmation SHALL increase evidence quality only for artifact
  kinds actually covered by artifact-state. Untracked imported artifacts SHALL
  remain advisory unless another canonical source grants authority.
- R029: Readiness SHALL be quality metadata and SHALL NOT activate a decision,
  constraint or relation.
- R030: Structured questions and contributions SHALL preserve answered/applied/
  superseded state and SHALL remain advisory event evidence unless their content
  has been applied to a canonical artifact.
- R031: Decision precedents SHALL be indexed as explicit project-wide context
  with their own authority class; they SHALL NOT silently become equivalent to a
  proposal acceptance decision.
- R032: Only explicitly cataloged governance rules, relevance criteria and
  project-definition fields SHALL become project-wide constraints. Generic
  free-text interpretation is excluded.
- R033: Work status SHALL be execution-state context linked through its Change
  Set and SHALL NOT alter proposal decision authority.

### Topology

- R034: THE topology SHALL use typed node namespaces for proposal, decision,
  choice, Change Set, Work, vertical section, capability, surface, command, file
  and feature entities.
- R035: A canonical relation SHALL store source, target and relation type.
  Incoming/outgoing direction SHALL be computed relative to a query and SHALL NOT
  create duplicate inverse edges.
- R036: Symmetric relations SHALL use deterministic endpoint ordering for
  identity while preserving both original evidence statements.
- R037: THE relation vocabulary and source-specific aliases SHALL be declarative
  and versioned. Unsupported relation types SHALL be quarantined as diagnostics,
  not promoted to active topology.
- R038: THE SYSTEM SHALL normalize relations from Change Set include/reference/
  decision/work metadata, `related-proposals.yml`, `impact-map.yml`,
  `conflict-analysis.yml`, project conflict memory, choice links and blockers,
  vertical coverage and Work-to-Change execution links.
- R039: Change Set frontmatter and companion relation files SHALL be reconciled
  using a documented precedence rule and SHALL emit divergence diagnostics when
  they disagree.
- R040: Equivalent edges asserted by multiple sources SHALL become one logical
  relation with deterministically ordered evidence, unless relation scope makes
  them semantically distinct.
- R041: Relations SHALL carry active, unresolved, historical or inactive state
  derived from source lifecycle without deleting historical evidence.
- R042: Traversal SHALL be cycle-safe, depth-bounded and fan-out-bounded.
- R043: Similarity signals such as same surface, same artifact, lexical overlap
  and heuristic vertical match SHALL remain retrieval reasons unless an explicit
  source asserts a topology relation.

### Explainable Retrieval

- R044: The first retrieval API SHALL support proposal IDs and idea text. Other
  target kinds SHALL retain their existing public behavior.
- R045: Retrieval SHALL query an in-memory index and SHALL perform no source-file
  reads after index construction.
- R046: Lexical normalization SHALL be deterministic and versioned, using Unicode
  NFKC normalization, case folding, Markdown syntax removal, punctuation
  splitting, a fixed stop-word policy and a fixed document-frequency rule for
  ubiquitous terms without stemming or network resources.
- R047: IDs, command names, file paths and other domain tokens SHALL remain
  searchable even when they contain punctuation or short segments.
- R048: `RetrievalPolicy` SHALL version candidate limits, eligibility filters,
  signal weights, per-signal caps, minimum score, grouping, diversity limits,
  tie-breaking, traversal depth and budget limits.
- R049: Every score SHALL equal the sum of reported signal contributions after
  per-signal caps and status penalties, clamped to the documented score range.
  Authority SHALL be used for eligibility and tie-breaking unless a distinct,
  reported authority contribution is configured.
- R050: Retrieval SHALL exclude the target itself, group claims by owning entity,
  suppress duplicate claim text deterministically and apply a per-owner result
  cap.
- R051: Historical proposals SHALL be returned only through an explicit relation,
  conflict/alternative evidence or a score above the historical threshold.
- R052: Recency SHALL use canonical dates such as decision date or `recorded_on`
  only as a final tie-breaker. Missing dates are neutral and filesystem time is
  forbidden.
- R053: The v1 score range SHALL be `0..100`, the minimum returned score SHALL be
  `15`, and candidate construction SHALL cap evaluated owner entities at `200`
  before deterministic ranking.
- R054: The v1 scoring table SHALL be versioned data with these initial capped
  contributions: active blocker/conflict `60`, explicit active relation `50`,
  applicable accepted decision `40`, shared declared capability/surface `25`,
  declared vertical section `20`, lexical overlap `20`, heuristic vertical match
  `8`, draft status penalty `-5` and historical status penalty `-15`.
  Applicability SHALL require an explicit relation, a declared domain match, or
  policy-qualified lexical overlap; acceptance status alone is insufficient.
- R055: Tie-breaking SHALL use score, authority rank, explicit-before-heuristic,
  active-before-unresolved-before-historical, canonical date and stable owner ID
  in that order.
- R056: A retrieval hit SHALL contain owner identity, selected record IDs,
  selected relation IDs, concise claim/decision/constraint payload, score,
  reported contributions and evidence references resolvable in the same packet.
  A target ID or opaque evidence ID alone is insufficient.
- R057: Retrieval with insufficient evidence SHALL return an empty neighborhood
  and an explicit reason; it SHALL NOT fall back to first-N registry records.

### Context Budgets

- R058: Budget enforcement SHALL occur after ranking and grouping and SHALL apply
  only to the new `nearby_context` portion of a compatibility context packet.
- R059: The v1 `small` budget SHALL allow at most 5 owner hits, 8 selected
  records, 8 relations, 2 reasons per hit, no transitive traversal and 12,000
  UTF-8 bytes after serialization.
- R060: The v1 `medium` budget SHALL allow at most 12 owner hits, 30 selected
  records, 24 relations, 5 reasons per hit, relation depth 1 and 40,000 UTF-8
  bytes after serialization.
- R061: Truncation SHALL remove the lowest-ranked optional material first,
  preserve deterministic order, retain evidence references for included claims
  and report truncation counts.

### Consumer Migration

- R062: Context packet integration SHALL add a versioned `nearby_context` object
  with policy version, source fingerprint, completeness, hits, diagnostics and
  truncation metadata while preserving legacy fields.
- R063: CLI text SHALL intentionally render nearby context; CLI YAML/JSON and MCP
  SHALL expose the same JSON-ready structure. Empty context SHALL have a stable,
  explicit representation.
- R064: Intake SHALL replace generic first-N semantic selection with idea-text
  retrieval while preserving controlled apply and owner decision boundaries.
- R065: Proposal explore, impact and synthesize prompts SHALL receive bounded
  nearby context appropriate to each phase, with provenance and no automatic
  writeback.
- R066: Next actions SHALL use normalized choice and relation semantics and SHALL
  not interpret proposal-local vote metadata as a project choice.
- R067: Existing registries MAY project normalized records, but SHALL remain
  derived and SHALL NOT be read back as semantic source by the index.

### Freshness, Cache And Performance

- R068: `source_fingerprint` SHALL include source-catalog version and a sorted
  entry for every expected source with normalized path, presence state and hash
  of captured bytes.
- R069: `index_semantic_fingerprint` SHALL include the source fingerprint plus
  extractor, authority and relation-policy versions. Retrieval packets SHALL
  additionally identify retrieval and budget-policy versions.
- R070: `generated_at` SHALL use an injected clock and SHALL be excluded from
  semantic equality and semantic fingerprints.
- R071: Materialized derived outputs SHALL report stale when any source presence,
  source hash, catalog version or relevant policy/generator version changes.
- R072: The initial implementation SHALL not persist a decision-context cache.
  Cache introduction requires a separate measured decision and an explicit
  design for path, atomic writes, locking, invalidation, schema migration,
  cleanup and rebuild.
- R073: Before context packet integration, profiling SHALL identify existing
  repeated scans and SHALL establish hard structural gates: one source discovery
  pass per build, at most one read/hash/parse per source and zero filesystem reads
  per query after build.
- R074: A representative scale fixture with at least 100 proposals, 25 Change
  Sets and 20 choices SHALL complete index build plus one proposal query within
  5 seconds in the normal test environment. Read/scan-count assertions are the
  primary non-flaky gate; elapsed time is a regression ceiling.

### Diagnostics

- R075: Diagnostics SHALL use stable namespaced codes, severity, fatality,
  root-relative source path, fragment/target when available, concise message and
  recovery guidance when practical.
- R076: A malformed optional source SHALL make its source partial and allow other
  sources to be indexed. Missing governed root, ambiguous duplicate owner
  identity or inability to construct a deterministic catalog SHALL fail the
  index build.
- R077: Diagnostic snippets SHALL be bounded and SHALL NOT expose absolute paths
  or duplicate full source contents.
- R078: The service SHALL distinguish unsupported source, malformed source,
  invalid target, unsupported relation, source divergence, duplicate identity,
  partial index and stale projection diagnostics.

## Non-Functional Requirements

- N001: The same source bytes and policy versions SHALL produce the same
  semantic index, ordering, scores and semantic fingerprints.
- N002: The feature SHALL run without network access.
- N003: Index construction SHALL be linear in cataloged source bytes plus emitted
  records and relations, excluding deterministic sort costs; nested full scans
  per proposal are forbidden.
- N004: Query execution SHALL operate on prebuilt maps/inverted indexes rather
  than scanning or reparsing the workspace.
- N005: No request-scoped snapshot SHALL survive into a later request unless it
  is keyed and revalidated by the full source and policy fingerprint.
- N006: Existing public behavior SHALL remain unchanged until its consumer slice
  is delivered.
- N007: Domain statuses and policies SHALL use enums or narrow literals rather
  than unconstrained strings.
- N008: Diagnostics and retrieval explanations SHALL be actionable and bounded.
- N009: All ordering SHALL use explicit stable sort keys rather than filesystem,
  dictionary or set iteration order.
- N010: The index SHALL remain useful when individual optional artifacts are
  malformed or absent.
- N011: The first slice SHALL remain independently mergeable and SHALL not change
  CLI, MCP, intake, prompts, registries or persistent storage.
- N012: Tests SHALL use synthetic fixtures and SHALL not copy real project
  `.p2p/` state as golden canonical data.

## Edge Cases And Errors

- E001: Missing optional artifacts produce diagnostics only when the source
  catalog expected them for the active extractor set.
- E002: Malformed frontmatter with a parseable Markdown body produces partial
  extraction only when the extractor can identify claims without inventing
  missing metadata.
- E003: Duplicate headings and list items remain separately traceable by
  deterministic occurrence.
- E004: A source modified during extraction is isolated by captured bytes; the
  following request sees the new fingerprint.
- E005: A second query in the same `P2PWorkspace` after a canonical write SHALL
  not reuse an unvalidated stale snapshot.
- E006: Legacy proposals without artifact-state remain advisory and are not
  treated as owner-confirmed.
- E007: Proposal-local `CHOICE-PROP-*` records remain local evidence, not project
  choice nodes requiring resolution.
- E008: A decided choice with missing target emits a diagnostic and does not
  create an active edge to a nonexistent node.
- E009: Conflicting Change Set relation sources retain all evidence, emit a
  divergence diagnostic and apply the documented precedence rule.
- E010: Multiple sources asserting the same edge merge evidence deterministically
  without multiplying its score.
- E011: Cyclic and high-fan-out relations terminate within policy depth and caps.
- E012: Generic idea text with only stop words or ubiquitous project terms
  returns no context rather than arbitrary proposals.
- E013: Historical proposals cannot outrank a directly applicable active decision
  solely through lexical overlap.
- E014: Missing canonical dates do not gain or lose score through filesystem
  timestamps.
- E015: A changed source with unchanged record count makes any materialized
  projection stale.
- E016: Deleting a future disposable cache does not lose project memory and the
  next build reproduces the semantic index.
- E017: Empty nearby context has a stable CLI structured and MCP representation.
- E018: Budget truncation never leaves a selected claim without its minimum
  evidence reference.

## Acceptance Criteria

- AC001: A service test builds an index from a temporary project and proves
  stable IDs, separate content hashes, spans, authority, completeness and
  root-relative evidence.
- AC002: Instrumented tests prove one discovery pass, at most one read/hash/parse
  per source and zero filesystem reads during retrieval.
- AC003: Parser table tests cover LF/CRLF, repeated headings, code fences, missing
  sections, malformed frontmatter and legacy placeholders.
- AC004: Authority tests cover every decision lifecycle outcome, conditional
  acceptance, status divergence, project choices, precedents, artifact state,
  readiness, questions, contributions and heuristic signals.
- AC005: Relation tests cover every cataloged node kind, alias normalization,
  duplicate evidence, Change Set divergence, invalid targets, cycles and
  historical/inactive edges.
- AC006: Retrieval golden tests prove exact score arithmetic, caps, ordering,
  grouping, diversity, historical thresholds, empty results and v1 budgets.
- AC007: Metamorphic tests prove invariance under filesystem enumeration order and
  repeated builds and prove fingerprint change after source or policy changes.
- AC008: A same-workspace regression test changes a source between requests and
  proves that the second result is fresh.
- AC009: The representative scale fixture satisfies R074 without nested scans.
- AC010: `p2p context --target PROP-XXX --budget small|medium` exposes compatible
  nearby context after its integration slice and preserves legacy fields.
- AC011: CLI text, CLI structured output and MCP payload contract tests agree on
  nearby-context semantics; existing non-proposal targets remain unchanged.
- AC012: Intake and proposal prompt integration select relevant context instead
  of first-N records and preserve controlled-apply boundaries.
- AC013: Next-action tests prove local vote metadata is not treated as an
  unresolved project choice.
- AC014: Freshness tests detect content, presence and policy changes and ignore
  `generated_at` for semantic equality.
- AC015: A before/after filesystem snapshot proves index build and retrieval do
  not modify canonical or derived project files.
