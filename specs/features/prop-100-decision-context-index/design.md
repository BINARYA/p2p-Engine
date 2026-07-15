# Design - PROP-100 Decision Context Index

## Requirements Covered

- R001-R078
- N001-N012
- E001-E018

## Design Goals

1. Preserve canonical P2P files and existing governance behavior.
2. Build one loss-aware semantic view from existing sources.
3. Make source authority and retrieval decisions explicit and inspectable.
4. Remove repeated scanning from request paths before adding more context work.
5. Deliver independently testable slices with compatibility gates.

## Key Decisions

- D001: Keep `ProjectDecisionContextService` as a stateless facade.
  `P2PWorkspace` may memoize the service object, but every `build_index()` creates
  a new request-scoped snapshot. The facade must not retain an index between
  requests unless a future fingerprint-validated cache design is approved.

- D002: Split the implementation into source, extraction, authority, topology,
  retrieval and freshness collaborators. This prevents a single service from
  becoming the new collection of ad hoc parsing and ranking rules.

- D003: Capture bytes once. Source hash, frontmatter, structured YAML and
  Markdown fragments are all derived from the same in-memory bytes. Existing
  helpers that reread a path cannot be used inside the extraction session.

- D004: Maintain an explicit source inclusion and exclusion matrix. Registries,
  publications, project summaries and generated prompts are consumers or
  projections, not semantic evidence.

- D005: Model canonicality, authority, activation, confidence and completeness
  as independent dimensions. Readiness and artifact confirmation are evidence
  quality; they do not become decisions.

- D006: Keep topology separate from similarity. Explicit or artifact-derived
  edges belong to the topology. Lexical overlap, same surface and heuristic
  vertical matches are retrieval signals.

- D007: Define retrieval as a versioned policy with exact arithmetic and budget
  limits. Every returned score must be reproducible from reported reasons.

- D008: Keep the first implementation in memory. A persistent cache is a later
  architectural decision, not a conditional task hidden inside this feature.

- D009: Make scan/read counts the primary performance gate. A wall-clock ceiling
  catches major regressions but does not replace structural assertions.

- D010: Migrate public consumers only after domain, topology, retrieval and
  performance gates pass. CLI and MCP changes occur together.

## Current-System Constraints

The implementation must account for these current behaviors:

- `foundation/markdown.py` expects a narrow heading layout and does not preserve
  spans or malformed-frontmatter diagnostics.
- `RegistryRecordBuilderService` mixes semantic extraction and projection and
  can rebuild Change Set records while iterating proposals.
- `ContextPacketService` independently requests proposal, choice, Change Set and
  Work summaries on each context request.
- `ProjectContextRendererService` currently uses fixed first-N registry slices.
- `decisions-map.yml` is intentionally lossy and cannot be an extraction source.
- project choice records and proposal-local `CHOICE-PROP-*` vote metadata have
  different semantics even when they appear in a shared projection.
- Change Set frontmatter and companion include/reference files may repeat the
  same lineage data.
- `ProjectVerticalService` has declared coverage and heuristic section matching;
  only declared coverage is an explicit relation.
- `ProposalReviewView` has a wider artifact catalog than
  `ProposalArtifactStateService`; not every artifact has owner-confirmation
  metadata.
- `P2PWorkspace` memoizes service instances, so request state must not live on a
  service instance.

## Proposed Module Boundaries

The exact filenames may be consolidated where local style warrants it, but the
following responsibilities remain separate and independently testable.

### Core Types

`src/p2p_engine/core/decision_context.py`

- enums and narrow literals;
- source, fragment, evidence, record, node and relation dataclasses;
- index and lookup structures;
- retrieval request, policy, reason, hit and packet contracts;
- diagnostics, completeness and manifest contracts;
- deterministic serializers that do not depend on dataclass `repr` output.

### Source Catalog And Snapshot

`src/p2p_engine/services/decision_context_sources.py`

- builds the versioned source catalog;
- normalizes root-relative POSIX paths;
- captures source presence and bytes;
- computes hashes from captured bytes;
- parses frontmatter, YAML and Markdown exactly once;
- exposes immutable `SourceDocument` and `ParsedFragment` objects;
- records source-access counters for tests and profiling.

### Extractors

`src/p2p_engine/services/decision_context_extractors.py`

- converts parsed sources into records, nodes and raw relation assertions;
- contains no filesystem access;
- contains no ranking behavior;
- emits diagnostics rather than silently dropping malformed data.

Extractors may be separate classes in one module initially. Split files only
when source-specific logic becomes difficult to navigate.

### Authority Policy

`src/p2p_engine/services/decision_context_authority.py`

- declares authority and activation rules as versioned data;
- resolves evidence-level authority;
- derives aggregate record/relation state from evidence;
- reports conflicting or unsupported authority combinations.

### Topology Normalizer

`src/p2p_engine/services/decision_context_topology.py`

- validates typed node targets;
- maps source vocabularies to controlled relation types;
- reconciles duplicate Change Set lineage sources;
- merges equivalent edges while retaining all evidence;
- provides cycle-safe adjacency maps.

### Retrieval

`src/p2p_engine/services/decision_context_retrieval.py`

- builds lexical and topology indexes from `DecisionContextIndex`;
- constructs bounded candidates;
- applies a versioned scoring policy;
- groups results by owner entity;
- assembles exact `small` and `medium` packets without filesystem access.

### Freshness

`src/p2p_engine/services/decision_context_freshness.py`

- computes source and semantic fingerprints;
- compares materialized projection manifests;
- receives an injected clock for observational metadata;
- does not persist a cache in the initial release.

### Facade

`src/p2p_engine/services/decision_context.py`

```python
class ProjectDecisionContextService:
    def build_index(self) -> DecisionContextIndex: ...
    def context_for_proposal(
        self, proposal_id: str, budget: ContextBudget
    ) -> DecisionContextPacket: ...
    def context_for_idea(
        self, idea: str, budget: ContextBudget
    ) -> DecisionContextPacket: ...
    def relations_for_target(self, target_id: str) -> tuple[DecisionContextRelation, ...]: ...
```

Each public method either accepts an explicit index or creates one new snapshot.
It never returns mutable internal dictionaries.

## Request Flow

1. `P2PWorkspace` obtains the memoized stateless facade.
2. The facade creates a fresh source catalog for the active extractor version.
3. The source component captures each selected file once and freezes the
   extraction session.
4. Extractors consume only captured documents/fragments.
5. Authority policy resolves evidence and record activation.
6. Topology normalizer validates and merges relation assertions.
7. The immutable index builds owner, node, adjacency and token lookup maps.
8. Retrieval evaluates candidates without filesystem access.
9. The budget assembler selects and truncates nearby context.
10. A consumer renders or embeds the packet without changing its semantics.

## Domain Contracts

### Source Document

```yaml
path: .p2p/proposals/PROP-001-example/proposal.md
source_kind: proposal_body
classification: canonical_semantic_source
presence: present
sha256: 0123...
parse_state: complete
diagnostic_ids: []
```

Raw bytes are request-private and are not serialized into public payloads.

### Parsed Fragment

```yaml
id: proposal-body:proposal:1
anchor: proposal
occurrence: 1
label: Proposal
text_sha256: 4567...
start_line: 20
end_line: 31
parse_state: complete
```

`id` identifies the semantic slot. `text_sha256` identifies current content.
Line spans are evidence metadata and never form record identity.

### Evidence

```yaml
source_path: .p2p/proposals/PROP-001-example/proposal.md
source_sha256: 0123...
source_kind: proposal_body
fragment_id: proposal-body:proposal:1
fragment_label: Proposal
span:
  start_line: 20
  end_line: 31
canonicality: canonical
authority: draft_proposal
activation: exploratory
confidence: explicit
completeness: complete
```

### Record

```yaml
schema_version: decision-context-record-v1
id: dcr:PROP-001:proposal:proposal:1
kind: proposal_claim
owner_type: proposal
owner_id: PROP-001
activation: exploratory
text: Add a derived decision context index.
text_sha256: 89ab...
evidence_ids:
  - dce:PROP-001:proposal-body:proposal:1
diagnostic_ids: []
```

The serialized record references evidence by ID. Internal objects may also keep
direct immutable references for efficient access.

### Node

```yaml
id: PROP-001
node_type: proposal
label: Decision Context Index
existence: cataloged
```

Identity nodes such as proposals, decisions, choices, Change Sets and Work must
exist in the source catalog. Value nodes such as capability or surface may be
created from a valid normalized explicit value. Vertical-section nodes must
exist in the selected vertical definition. A planned file value does not need to
exist on disk unless the source explicitly claims current file existence.

### Relation

```yaml
schema_version: decision-context-relation-v1
id: dcrl:PROP-001:depends_on:PROP-012:project
source_id: PROP-001
source_type: proposal
target_id: PROP-012
target_type: proposal
relation_type: depends_on
scope: project
activation: active
authority: artifact_derived
confidence: explicit
evidence_ids:
  - dce:PROP-001:related-proposals:depends-on:1
```

Query direction is computed from whether the query target equals `source_id` or
`target_id`. Symmetric edges sort endpoints for identity.

### Index

`DecisionContextIndex` contains immutable tuples/maps for:

- sources by normalized path;
- fragments by source and ID;
- evidence by ID;
- records by ID and owner;
- nodes by typed ID;
- relations by ID;
- outgoing and incoming adjacency;
- normalized token to owner/record postings;
- diagnostics;
- source and semantic fingerprints;
- schema and policy versions;
- completeness.

The index has no method that writes to disk.

## Stable Identity Rules

1. Normalize source paths relative to project root using POSIX separators.
2. Preserve explicit P2P owner IDs exactly after validation.
3. Normalize section anchors using a fixed ASCII slug function.
4. Add a one-based occurrence for duplicate sections or repeated list slots.
5. Compose identity from owner, source kind, record kind, anchor and occurrence.
6. Hash the composition only to keep IDs compact; retain the readable identity
   fields in the record.
7. Keep content hash separate.
8. Sort all emitted objects by explicit `(owner_type, owner_id, source_path,
   fragment_id, kind, id)` keys.

A source rename changes identity. A text edit in the same semantic slot changes
content hash but not identity. Inserting a repeated item may change subsequent
occurrences; this is documented rather than hidden with fuzzy identity matching.

## Parsing Design

The decision-context parser initially lives beside the source snapshot so it can
parse captured text. It must not globally replace `foundation/markdown.py`
without running all existing parser consumers.

### Markdown

- normalize line endings for parsing while hashing original bytes;
- recognize ATX level-two headings outside fenced code blocks;
- allow zero or more blank lines after a heading;
- preserve duplicate heading occurrence and line spans;
- preserve section text without re-rendering it;
- mark legacy placeholders as empty, not missing;
- emit a duplicate-section advisory when an extractor expected one section.

### Frontmatter And YAML

- distinguish no delimiter, empty frontmatter and malformed YAML;
- parse from captured text, never by reopening the path;
- require mapping/list shapes per source descriptor;
- detect duplicate mapping keys when practical and emit a diagnostic;
- allow body extraction after malformed frontmatter only if the extractor does
  not need the malformed fields to assign owner or authority.

## Source Catalog And Authority Matrix

| Source family | Classification | Initial semantic use |
| --- | --- | --- |
| Proposal body | canonical semantic source | claims and proposal state |
| Proposal decision | canonical semantic source | outcome, reason, approver, date and activation |
| Related proposals, impact and conflict artifacts | governed artifact evidence | relation assertions with artifact-state quality when available |
| Proposal questions | quality/advisory metadata | answered/applied/superseded evidence state |
| Contributions | advisory event evidence | lineage and supersession history only |
| Readiness and artifact-state | quality metadata | completeness/confirmation, never decision activation |
| Project choice, decision and links | canonical semantic source | selected option, reason and blockers |
| Project conflict memory | canonical semantic source | explicit conflict/winner/history |
| Change Set source and relation files | canonical semantic source | proposal/decision lineage and references |
| Work manifest/status | execution-state metadata | Work-to-Change execution state |
| Declared vertical coverage | canonical semantic source | explicit section relation |
| Heuristic vertical match | derived retrieval signal | low-confidence reason only |
| Decision precedents | canonical project context | explicit precedent authority |
| Cataloged governance/project-definition fields | canonical project context | bounded project-wide constraints |
| Registries and decisions map | derived projection, excluded | consumer compatibility only |
| Project overview/scope/brief/publication | generated narrative, excluded | no extraction |
| Generated prompts and outputs | generated output, excluded | no extraction |
| Decision-context manifests/caches | derived infrastructure, excluded | freshness only |

`SourceCatalogVersion` changes whenever a source family or classification changes.

### Authority Dimensions

Example v1 authority ranking, highest first:

1. `accepted_decision`
2. `conditionally_accepted_decision`
3. `decided_project_choice`
4. `explicit_decision_precedent`
5. `project_definition_constraint`
6. `accepted_proposal_context`
7. `owner_confirmed_evidence`
8. `system_state`
9. `draft_proposal`
10. `agent_proposed_evidence`
11. `proposal_local_vote`
12. `historical_proposal`
13. `heuristic_signal`

Authority rank determines eligibility and tie-breaking. It does not add an
unreported score.

### Decision Lifecycle

| Outcome/state | Activation | Treatment |
| --- | --- | --- |
| `accepted` | active | decision and linked proposal claims are active context |
| `accepted_with_changes` | active, qualified | reason is an active qualifier; proposal claims are not unconditional |
| `rejected` | historical | rationale and alternative remain available above historical threshold |
| `deferred` | unresolved/historical | not an active constraint; reason may explain deferral |
| `split` | historical | source proposal links to explicit split targets when available |
| `merged_into_other` | historical | relation to target proposal is active lineage |
| `superseded` | historical | supersession edge identifies current source when available |
| pending/draft | exploratory | proposal claims remain exploratory |
| unknown legacy | unresolved | diagnostic and conservative advisory authority |

If proposal status and decision outcome disagree, the decision file controls
decision authority and a `DC-AUTHORITY-STATUS-DIVERGENCE` diagnostic is emitted.
No source file is repaired.

## Claim Extraction

### Proposal Body Mapping

| Section | Record kind | Multiplicity |
| --- | --- | --- |
| Problem | `problem` | one per section occurrence |
| Goals | `goal` | list item when list-shaped, otherwise one claim |
| Non-Goals | `non_goal` | list item when list-shaped, otherwise one claim |
| Proposal | `proposal_claim` | one per section occurrence |
| Acceptance Criteria | `acceptance_criterion` | list item when list-shaped, otherwise one claim |
| Frontmatter/status | `proposal_state` | one |

List splitting is structural and deterministic. Nested list content remains with
its top-level item. Empty placeholders produce no claim but preserve source
completeness metadata.

### Decision Mapping

The decision source produces:

- one decision-state record;
- one rationale/qualifier record when reason is present;
- approver and date provenance;
- evidence links to proposal records affected by the outcome;
- lifecycle relations for split, merge or supersession when targets exist.

There is no invented "selected decision text" when the current decision format
does not contain it. The accepted content is represented by the evidence chain
from decision outcome to proposal claims.

## Artifact Metadata Resolution

Artifact authority cannot rely solely on `ProposalArtifactStateService` because
that service tracks only a subset of proposal artifacts.

Create a `SourceMetadataResolver` that combines:

- the artifact catalog used by proposal review;
- artifact-state entries where the artifact kind is tracked;
- import/provenance metadata exposed by existing services;
- source defaults from the source catalog.

If no confirmation source exists, the artifact remains `governed_import` or
`advisory`; absence of an artifact-state entry never implies owner confirmation.

## Topology Design

### Node Types

- identity nodes: proposal, decision, choice, change, work;
- declared domain nodes: vertical section;
- normalized value nodes: capability, surface, feature, command, file.

Node IDs are namespaced internally even where the display ID is already unique.
Target validation is node-type-specific.

### Controlled Relation Vocabulary

Initial v1 types:

- `includes`
- `references`
- `depends_on`
- `blocks`
- `conflicts_with`
- `supersedes`
- `merged_into`
- `split_into`
- `implements`
- `selected_by`
- `affects_capability`
- `affects_surface`
- `affects_feature`
- `touches_command`
- `touches_file`
- `maps_to_vertical_section`
- `derived_from`

Source aliases map to this vocabulary. Unknown values emit
`DC-RELATION-UNSUPPORTED-TYPE` and remain outside active adjacency.

### Relation Identity And Merge

- directed key: `(source_node, relation_type, target_node, scope)`;
- symmetric key: sorted endpoints plus relation type and scope;
- equivalent assertions merge into one relation;
- evidence remains separate, sorted by source path and fragment ID;
- scoring sees the logical edge once;
- aggregate activation uses the strongest valid current evidence and retains
  historical evidence;
- incompatible active assertions emit a conflict diagnostic.

### Change Set Reconciliation

For semantically duplicated lineage fields:

1. explicit companion relation files are the structured relation source;
2. Change Set frontmatter is an independent corroborating assertion;
3. matching assertions merge evidence;
4. disagreement emits `DC-SOURCE-DIVERGENT-CHANGE-LINKS`;
5. no registry projection participates in resolution.

### Traversal

- adjacency stores visited relation IDs and node IDs;
- `small` uses depth 0, meaning direct edges only;
- `medium` uses at most one transitive hop after direct neighbors;
- fan-out is capped by the retrieval policy before expansion;
- cycles terminate through visited-node and visited-edge sets;
- transitive hits report every relation used in the path.

## Retrieval Design

### Normalization Policy v1

1. Apply Unicode NFKC.
2. Apply Unicode case folding.
3. Remove Markdown formatting markers while retaining visible text.
4. Split punctuation and whitespace.
5. Preserve normalized full IDs, command names and paths as domain tokens in
   addition to their segments.
6. Remove a fixed, versioned Italian/English stop-word set.
7. Mark a non-domain token ubiquitous when it appears in at least 60 percent of
   owner entities and the index has at least 10 owners; ubiquitous tokens do not
   create candidates or earn lexical score.
8. Do not stem, lemmatize or call an external service.

The stop-word list and normalizer version are test fixtures, not ambient locale
behavior.

### Prebuilt Lookups

- token to record IDs;
- token to owner IDs;
- owner to active/historical records;
- owner to incoming/outgoing relation IDs;
- node type and ID to node;
- capability/surface/vertical section to owner IDs;
- decision/choice applicability to affected owner IDs.

Retrieval receives these maps and no path objects or source readers.

### Candidate Construction

For a proposal target:

1. direct topology neighbors;
2. applicable accepted decisions and decided choices;
3. blockers and conflicts;
4. shared declared capability, surface and vertical-section owners;
5. lexical postings from title, problem, goal, proposal and acceptance-criterion
   claims; non-goals and historical rationale do not provide positive lexical
   query tokens in v1;
6. historical alternatives only when explicit or above threshold;
7. one transitive hop only for `medium`.

For idea text:

1. normalize query tokens;
2. select owners from token and domain-value postings;
3. attach applicable project-wide precedents/constraints only when a declared
   applicability token, capability, surface or vertical section matches;
4. return empty if only stop words or ubiquitous low-signal terms remain.

Candidate owners are deduplicated and capped at 200 before scoring. If more than
200 qualify, pre-order by strongest explicit signal, token match count and owner
ID.

An accepted decision or project-wide precedent is "applicable" in v1 only when
at least one of these conditions holds:

- an explicit topology relation reaches its owner;
- a declared capability, surface or vertical section matches;
- lexical overlap contributes at least 10 points and contains at least one
  domain token or rare token.

Acceptance status alone never broadcasts a decision into every context packet.

### Scoring Policy v1

| Signal group | Contribution/cap |
| --- | ---: |
| Active blocker or conflict | +60 |
| Other explicit active relation | +50 |
| Applicable accepted decision | +40 |
| Shared declared capability or surface | +25 total |
| Shared declared vertical section | +20 |
| Lexical overlap | +20 maximum |
| Heuristic vertical match | +8 maximum |
| Draft candidate | -5 |
| Historical candidate | -15 |

Rules:

- blocker/conflict and generic explicit-relation contributions are one relation
  signal group; the same edge does not earn both;
- duplicate evidence for one edge does not multiply score;
- lexical contribution uses unique non-ubiquitous query tokens. Domain tokens
  have weight 3, tokens present in at most `max(2, ceil(owner_count / 10))`
  owners have weight 2 and other tokens have weight 1. Contribution is
  `floor(20 * matched_query_weight / total_query_weight)` and is zero when the
  denominator is zero;
- total score is the sum of emitted contributions clamped to `0..100`;
- minimum returned score is 15;
- a historical owner requires explicit conflict/alternative/lineage evidence or
  score at least 35 after penalty;
- the query target is always excluded;
- one hit is emitted per owner entity.

### Tie-Breaking

1. score descending;
2. authority rank descending;
3. explicit signal before heuristic-only signal;
4. active before unresolved before historical;
5. canonical date descending only when both candidates have a canonical date;
6. stable owner type and ID ascending.

Missing dates skip step 5 and therefore remain neutral.

### Retrieval Hit

```yaml
owner_id: PROP-012
owner_type: proposal
score: 87
activation: active
selected_record_ids:
  - dcr:PROP-012:decision:reason:1
selected_relation_ids:
  - dcrl:PROP-100:depends_on:PROP-012:project
summary:
  decisions:
    - Preserve Markdown and YAML as canonical state.
  constraints: []
  claims: []
reasons:
  - signal: explicit_active_relation
    contribution: 50
    detail: PROP-100 depends_on PROP-012
  - signal: applicable_accepted_decision
    contribution: 40
    detail: accepted decision shares capability decision-memory
evidence_ids:
  - dce:PROP-012:decision:reason:1
```

The packet serializer verifies that reported contributions reproduce `score`
after clamp.

## Budget Policy v1

Budgeting applies to the serialized `nearby_context` object, measured through a
canonical compact JSON representation encoded as UTF-8. CLI formatting does not
change semantic selection.

| Limit | `small` | `medium` |
| --- | ---: | ---: |
| Owner hits | 5 | 12 |
| Selected records | 8 | 30 |
| Relations | 8 | 24 |
| Reasons per hit | 2 | 5 |
| Transitive depth | 0 | 1 |
| Serialized bytes | 12,000 | 40,000 |

Truncation order:

1. reasons beyond the required strongest reason;
2. optional historical claim text;
3. lower-ranked relations not needed to explain a selected hit;
4. lower-ranked records within a hit;
5. lowest-ranked hits.

Schema/policy/fingerprint/completeness fields, one explanation per included hit
and minimum evidence for included claims are never removed. The packet reports
original and retained counts.

## Diagnostics Contract

Example stable codes:

- `DC-SOURCE-MISSING-OPTIONAL`
- `DC-SOURCE-MALFORMED-YAML`
- `DC-SOURCE-DUPLICATE-KEY`
- `DC-SOURCE-DUPLICATE-SECTION`
- `DC-SOURCE-DIVERGENT-CHANGE-LINKS`
- `DC-IDENTITY-DUPLICATE-OWNER`
- `DC-AUTHORITY-STATUS-DIVERGENCE`
- `DC-RELATION-INVALID-TARGET`
- `DC-RELATION-UNSUPPORTED-TYPE`
- `DC-INDEX-PARTIAL`
- `DC-PROJECTION-STALE`
- `DC-RETRIEVAL-EMPTY`
- `DC-RETRIEVAL-TRUNCATED`

Each diagnostic contains:

```yaml
code: DC-RELATION-INVALID-TARGET
severity: warning
fatal: false
source_path: .p2p/proposals/PROP-001-example/related-proposals.yml
fragment_id: relation:depends-on:1
target_id: PROP-999
message: Related proposal target is not cataloged.
recovery: Correct or remove the relation through the supported proposal workflow.
```

Paths are root-relative. Optional snippets are capped at 160 Unicode characters.
An individual malformed optional source yields a partial index. Missing governed
root, duplicate owner identity or nondeterministic catalog construction is fatal.

## Freshness Design

### Source Fingerprint

Canonical JSON input, sorted by path:

```yaml
source_catalog_version: decision-context-sources-v1
sources:
  - path: .p2p/proposals/PROP-001-example/proposal.md
    presence: present
    sha256: 0123...
  - path: .p2p/proposals/PROP-001-example/decision.md
    presence: missing
    sha256: null
```

The hash includes expected missing sources for the active extractor set so file
creation/deletion changes freshness.

### Semantic Fingerprint

```yaml
source_fingerprint_sha256: ...
extractor_version: decision-context-extractors-v1
authority_policy_version: decision-context-authority-v1
relation_policy_version: decision-context-relations-v1
```

Retrieval packets add:

```yaml
retrieval_policy_version: decision-context-retrieval-v1
budget_policy_version: decision-context-budget-v1
```

`generated_at` is observational metadata supplied by an injected clock. It is
not part of semantic equality, source fingerprint or semantic fingerprint.

### Materialized Projection Manifest

No manifest is written by index construction. If a consumer already persists a
derived projection, its adjacent/contracted manifest contains schema version,
generator version, generated time, source fingerprint, semantic fingerprint and
input paths/hashes. Writes use existing atomic file helpers.

## Cache Decision

The initial implementation has no persistent decision-context cache. After the
scale and real-project measurements, a decision note records one of:

- `deferred`: in-memory rebuild satisfies the thresholds;
- `separate_feature_required`: persistence is justified.

The second outcome requires a new specification covering durable path, ownership,
atomic replacement, process locking, invalidation, schema migration, corruption,
cleanup and rebuild. It cannot be implemented under a conditional task here.

## Performance Guardrails

### Structural Gates

- one bounded source-catalog discovery pass per index build;
- at most one byte read, hash and parse per selected source;
- no registry projection read as semantic input;
- no per-proposal full Change Set scan;
- no filesystem read during candidate construction, scoring or packet assembly;
- build complexity proportional to cataloged source bytes, records and relations;
- query complexity proportional to postings/candidate cap, not workspace size.

Tests inject a source accessor/counter rather than relying on global mocking.

### Scale Fixture

A deterministic synthetic workspace contains at least:

- 100 proposals with mixed decision states;
- 25 Change Sets with overlapping references;
- 20 project choices plus proposal-local votes;
- conflicts, vertical mappings and malformed optional artifacts;
- enough common vocabulary to test false positives.

Index build plus one proposal query must stay under 5 seconds in the normal test
environment. Scan/read assertions are the primary CI signal. A benchmark note
also records current real-project `p2p context` baseline and call-path hotspots
before Slice E integration.

## Consumer Migration

### Slice A: Domain, Sources And Proposal Decisions

Deliver typed contracts, source snapshot, robust parser, proposal/decision
extractors and the stateless facade. No public changes.

### Slice B: Authority And Topology

Add source metadata resolution, complete lifecycle authority, project-wide
precedents, typed nodes and relation normalizers. No public changes.

### Slice C: Retrieval And Budgets

Add versioned normalization/scoring, prebuilt indexes, golden/adversarial tests
and semantic packets. No existing command behavior changes.

### Slice D: Performance Remediation Gate

Profile current context construction, remove repeated scans on the integration
path and satisfy structural/scale gates. Slice E cannot start until this gate
passes or a documented owner-approved exception exists.

### Slice E: Context Packet, CLI And MCP

Add `nearby_context` for proposal targets, preserve legacy and non-proposal
behavior, and update text/structured CLI and MCP output tests together.

### Slice F: Intake And Proposal Prompts

Replace first-N semantic context with bounded retrieval. Preserve controlled
apply and phase-specific prompt behavior.

### Slice G: Next Actions And Projections

Use normalized choice/relation semantics for next actions. Decide explicitly
whether old relation registries remain legacy projections or gain a new
versioned projection without becoming semantic input.

### Slice H: Freshness And Materialized Manifests

Add fingerprints and stale checks where a derived consumer persists output.
Keep index construction in memory.

### Slice I: Cache Decision

Measure, record `deferred` or open a separate cache feature. No cache code is
delivered in this feature.

## Public Contract

### Context Packet Addition

```yaml
nearby_context:
  schema_version: decision-context-packet-v1
  retrieval_policy_version: decision-context-retrieval-v1
  budget_policy_version: decision-context-budget-v1
  budget: small
  source_fingerprint_sha256: ...
  completeness: complete
  hits: []
  evidence: []
  diagnostics: []
  truncation:
    truncated: false
    original_counts: {}
    retained_counts: {}
```

The field is absent before Slice E. After integration it is present for supported
proposal targets, including a stable empty object. Non-proposal targets retain
their prior payload until separately specified.

### CLI

- text output renders a concise "Nearby decision context" section only for the
  supported target and includes score plus strongest reason;
- YAML/JSON output uses the public packet structure without renderer-specific
  selection;
- rendering never reranks or truncates hits.

### MCP

- `p2p_context` input schema remains unchanged unless new arguments are added;
- handler serialization supports enums, paths and optional date/time values in
  JSON-ready form;
- payload contract tests assert the output shape and parity with workspace
  service output;
- the tool remains read-only.

## Test Strategy

### Unit And Table Tests

- source classification and exclusions;
- parser line-ending, heading, fence, frontmatter and duplicate cases;
- stable IDs and content hashes;
- complete decision lifecycle and authority matrix;
- relation aliases, identity, merge and target validation;
- score arithmetic, caps, tie-breaking and budgets;
- fingerprint and clock behavior.

### Metamorphic And Invariant Tests

- reversed/random filesystem enumeration yields the same semantic index;
- repeated build with identical bytes yields identical semantic output;
- generated time changes observational metadata only;
- changing content/presence/policy changes the expected fingerprint;
- same workspace after a write returns fresh data;
- build/query leaves a before/after filesystem snapshot unchanged;
- duplicate evidence does not duplicate score;
- cycles and fan-out terminate within limits.

### Golden And Adversarial Fixtures

Use small synthetic projects for readable expected output. Include accepted,
conditional, draft, deferred, rejected, split, merged and superseded proposals;
choices/local votes; conflicts; Change Set divergence; artifact-state mismatch;
vertical declared/heuristic signals; malformed optional files; generic text;
duplicate terms and false-positive historical candidates.

### Public And Performance Tests

- context service compatibility;
- CLI text and structured output;
- MCP payload shape and read-only behavior;
- unchanged `CHANGE`, `CHOICE`, `WORK` and untargeted context behavior;
- intake and prompt controlled-apply boundaries;
- next-action choice semantics;
- read/scan counters and representative scale ceiling.

## Backward Compatibility

- Existing context fields remain until a separate versioned removal.
- Existing registry files remain generated by their current commands.
- Existing command and MCP tool names remain stable.
- Existing non-proposal target behavior remains unchanged in the first public
  integration.
- No consumer reads the new index until its own slice and tests are complete.
- Existing Markdown helpers are not globally replaced without full regression
  coverage.

## Deferred Decisions

- persistent cache technology and location;
- embeddings as an additive signal;
- topology writeback or relation authoring workflow;
- public normalized-relations registry schema;
- retrieval for Change Set, Choice and Work targets;
- deeper vertical/governance natural-language modeling.
