# Design - Vertical-Aware Project Memory Performance And Incremental Projection

## Requirements Covered

- Block A: A-R001..048.
- Block B: B-R001..042.
- Block C: C-R001..025.
- Block X: X-R001..009.
- Cross-cutting: N001..018, E001..012, and AC001..025.

## Design Goals

- Remove unnecessary global work before adding persistence.
- Make read consistency, source capture, and memoization explicit.
- Keep fast reads honest about what they did not verify.
- Keep canonical authority and derived project memory separate.
- Build the current project around the active vertical and its sections.
- Reuse current lifecycle, decision-context, readiness, transaction, and
  fingerprint policies instead of creating competing semantics.
- Make every optimization testable with structural counters.
- Keep file-backed derived state sufficient until measurement proves otherwise.

## Current Architecture Findings

The current code already contains useful local patterns:

- `DecisionContextSourceService` performs one discovery and records per-source
  read, hash, and parse counts.
- `ProjectReadinessSourceAccess` caches captured bytes for one readiness build.
- `AtomicMutationWriter` provides source preconditions, locking, staging,
  rollback, and recovery.
- `ProjectStateService`, software specs, publication, and decision context
  already use semantic fingerprints in parts of the derived-state graph.
- `ContextPacketService`, `DerivedFreshnessService`, `ProjectProgressService`,
  and `NextActionService` accept some manually assembled snapshots.

The patterns are not yet shared. Composite reads pass untyped dictionaries,
services still call global providers independently, and some callers build
expensive values that are not needed by the requested output.

## Key Decisions

- D001: Deliver one feature with mandatory gates between performance,
  vertical-memory generation, consumer convergence, and persistence evaluation.
  Rationale: the architecture is shared, but the immediate performance fix must
  remain independently releasable.

- D002: Introduce a typed, lazy `WorkspaceReadContext`, not an eager aggregate
  snapshot.
  Rationale: eager construction would make every command pay for every domain.

- D003: Put source-byte capture and parse memoization below domain services in a
  request-scoped `WorkspaceDocumentStore`.
  Rationale: lifecycle, validation, readiness, and decision context currently
  solve overlapping source-access problems independently.

- D004: Use optimistic read consistency with captured directory snapshots and
  source identities, retrying once on concurrent change.
  Rationale: CLI reads should remain non-blocking while MCP must not return mixed
  revisions during concurrent writes.

- D005: Split schema preflight from complete workspace layout validation.
  Rationale: a targeted lifecycle read needs compatibility and recovery state,
  not validation of every ledger.

- D006: Make lifecycle and vertical processing batch-first internally.
  Rationale: memoization alone cannot correct repeated collection scans.

- D007: Keep fast and deep paths as compositions of the same providers.
  Rationale: independent implementations would drift semantically.

- D008: Use existing explicit `validate` and `project freshness` commands as the
  deep paths instead of requiring a new `status --deep` surface.
  Rationale: the current CLI already exposes the correct explicit operations.

- D009: Treat registries as materialized read models only after adding source
  identity and atomic bundle generation.
  Rationale: current count-based status cannot prove same-count semantic
  freshness, and separately written files can expose mixed generations.

- D010: Use cache-aside fallback from derived read models to canonical batch
  computation.
  Rationale: an optimization must never become a correctness dependency.

- D011: Add C-accelerated YAML behind shared semantic loaders only after
  algorithmic fixes.
  Rationale: faster parsing does not correct quadratic parsing and must preserve
  unique-key validation.

- D012: Store vertical project memory as a structured derived read model under
  `.p2p/project/vertical-memory/`.
  Rationale: this is project-level operational memory, not canonical intent or
  an external publication.

- D013: Build vertical memory from current authority and explicit topology,
  reusing decision-context and lifecycle semantics.
  Rationale: a second authority extractor would create divergent project truth.

- D014: Keep declared section evidence authoritative and heuristic section
  matches advisory.
  Rationale: text similarity cannot replace owner-confirmed coverage.

- D015: Store structured contributions and evidence, not only synthesized prose.
  Rationale: readiness and deterministic rendering require inspectable facts.

- D016: Do not attempt automatic semantic conflict resolution or LLM-authored
  consolidation in this feature.
  Rationale: unresolved contradictions require explicit evidence or owner
  authority; free-form incremental prose would drift.

- D017: Require full and incremental builders to produce the same complete
  candidate generation.
  Rationale: incremental computation must be an optimization, not a second
  semantic implementation.

- D018: Commit registry and vertical-memory bundles through existing transaction
  infrastructure.
  Rationale: readers must observe either the previous complete generation or the
  next complete generation.

- D019: Keep read commands side-effect free. Persistent vertical-memory refresh
  occurs through `p2p project refresh` or a reported post-commit derived stage.
  Rationale: a read must not hide durable workspace writes.

- D020: Let canonical mutation success stand even if a post-commit derived
  refresh fails.
  Rationale: derived failure cannot rewrite governance history.

- D021: Make readiness consume structured vertical memory while preserving the
  existing classifier and independent axes.
  Rationale: optimization must not redefine project readiness.

- D022: Use vertical memory for untargeted context and decision context for
  targeted neighborhood retrieval.
  Rationale: the compact project view should avoid rebuilding the complete
  evidence index when no target-specific neighborhood is requested.

- D023: Keep persistence evaluation evidence-only.
  Rationale: current data volume and measured file-read cost do not justify a
  database before the algorithmic and read-model work is complete.

- D024: Keep section memory compact through exact material fragments and source
  references, not copied proposal bodies or embedded downstream products.
  Rationale: a read model that duplicates every source artifact would reproduce
  the context-growth problem in a different directory.

- D025: Limit automatic post-commit work to no-op or incremental refresh against
  a current compatible generation.
  Rationale: a canonical governance mutation must not conceal an unbounded full
  project rebuild or inherit its latency and failure surface.

## Target Architecture

```text
canonical sources
    |
    v
WorkspaceReadContext
    |- WorkspaceDocumentStore
    |- schema preflight / deep validation
    |- lifecycle batch
    |- vertical batch
    |- decision context
    |- readiness / progress
    `- freshness / next actions
    |
    +--> canonical in-memory result
    |
    `--> derived read models
          |- registry bundle
          |- vertical project memory
          |- existing project projections
          `- existing publication/spec outputs

vertical project memory
    |- readiness classifier
    |- untargeted context
    |- next-action project gaps
    `- vertical-first project rendering
```

Canonical sources remain authoritative. Every arrow toward a read model is
deterministic and reversible. No arrow from a read model changes authority.

## Block A Design

### WorkspaceReadContext

The public request abstraction is conceptually:

```python
class WorkspaceReadContext:
    root: Path
    documents: WorkspaceDocumentStore
    counters: ReadOperationCounters

    def schema_preflight(self) -> WorkspaceSchemaPreflight: ...
    def schema_status(self) -> WorkspaceSchemaStatus: ...
    def proposal_lifecycles(self, ids: Iterable[str] | None = None) -> Mapping[str, LifecycleView]: ...
    def active_vertical(self) -> ActiveProjectVertical: ...
    def vertical_pack(self, vertical_id: str | None = None) -> VerticalPack: ...
    def registry_status(self) -> RegistryStatus: ...
    def registry_view(self, name: str) -> RegistryView: ...
    def proposal_summaries(self) -> tuple[ProposalSummary, ...]: ...
    def decision_context_index(self) -> DecisionContextIndex: ...
    def vertical_memory(self, allow_canonical_fallback: bool = True) -> VerticalMemoryView: ...
    def project_progress(self, include_heuristics: bool = False) -> ProjectProgress: ...
    def project_readiness(self) -> ProjectReadinessResult: ...
    def fast_freshness(self) -> FastFreshnessSummary: ...
    def deep_freshness(self) -> DerivedFreshnessStatus: ...
    def next_actions(self, limit: int | None = None) -> tuple[NextAction, ...]: ...
    def finalize(self) -> ReadConsistencyResult: ...
```

Provider methods are lazy memoized functions. A provider key includes all
semantic arguments, such as selected IDs, vertical ID, heuristic mode, target,
and budget. Mutable lists and dictionaries are not exposed directly.

Existing `P2PWorkspace` methods remain compatibility facades:

```python
def proposal_summaries(self, status=None, *, read_context=None):
    context = read_context or self.read_context()
    values = context.proposal_summaries()
    return filter_status(values, status)
```

A composite public method creates one context and passes it through every
consumer. Domain services no longer call back into unrestricted
`P2PWorkspace` methods when a context is available.

### WorkspaceDocumentStore

The document store owns request-private captured bytes:

```python
@dataclass(frozen=True)
class CapturedDocument:
    relative_path: str
    exists: bool
    physical_sha256: str | None
    size: int
    mtime_ns_observed: int | None
    content: bytes | None  # private to the request
```

Public serializers never expose `content`. The store provides:

```python
capture(path)
capture_optional(path)
discover(directory, predicate)
text(path, encoding="utf-8")
yaml(path, loader_contract="safe-v1")
hash(path)
```

Cache keys:

```text
capture: resolved path
text: resolved path + physical hash + encoding
yaml: resolved path + physical hash + loader contract
discovery: directory + discovery policy
```

`loader_contract` distinguishes normal safe parsing, unique-key parsing,
frontmatter parsing, workspace-schema parsing, and decision-ledger codecs.

### Read Consistency

The context records:

- discovered directory membership and entry metadata;
- physical hashes for captured files;
- the workspace mutation-lock identity observed at request start and end;
- source catalog policy versions used by providers.

Before returning a composite result, `finalize()` verifies all captured files
and discoveries. If they changed:

1. the facade discards the result;
2. it creates a new context and retries once;
3. a second change returns `P2P_READ_CONCURRENT_CHANGE` with no mixed payload.

Single-file targeted reads may use the same finalization path. Deep reads do not
hold the mutation lock for their full duration; existing write preconditions
remain the write-side authority.

### Schema Split

`WorkspaceSchemaPreflight` contains only:

```yaml
schema_path: .p2p/project/workspace-schema.yml
declaration_state: declared
current_version: 3
target_version: 3
layout_class: current
migration_required: false
recovery_required: false
contract_version: 1
```

It reads schema declaration and recovery state but does not enumerate proposal
ledgers, parse every vertical, or run alignment advisories.

`WorkspaceSchemaService.status()` remains the complete public status for deep
schema inspection. It is refactored to receive optional captured sources and a
preflight, then adds layout findings exactly once.

Lifecycle target and batch reads depend on preflight. Workspace validation
depends on full status and shares parsed ledgers with lifecycle validation.

### Lifecycle Batch Engine

The internal API is:

```python
evaluate_many(
    proposal_ids: Iterable[str],
    *,
    preflight: WorkspaceSchemaPreflight,
    documents: WorkspaceDocumentStore,
    strict: bool = False,
) -> Mapping[str, ProposalDecisionLifecycleView]
```

Rules:

- normalize and sort IDs once;
- resolve proposal directories once;
- parse one v3 ledger per selected proposal;
- capture legacy proposal/decision projections once per selected v2 proposal;
- preserve current diagnostics and binding semantics;
- never call full schema status from the proposal loop;
- make `status(id)` and `capture_all()` wrappers over the same evaluator.

### Vertical Batch Engine

The vertical request state contains:

```python
VerticalReadState(
    active,
    pack,
    valid_section_ids,
    section_terms,
    term_frequency,
    compiled_patterns,
)
```

The batch coverage evaluator receives proposal IDs and captured coverage bytes.
The heuristic evaluator receives captured proposal texts and the precompiled
term model. It returns explicit computation state:

```yaml
heuristics:
  state: computed | not_requested | unavailable
  policy_version: 1
  candidates: []
```

Authoritative progress calls declared coverage only. Readiness detail or
coverage suggestion commands may request heuristic computation.

### Cost-Class Matrix

| Provider or command | Cost class | Allowed global work |
| --- | --- | --- |
| `check` | fast | fixed required-path checks |
| `status` | fast | schema preflight, registry/vertical-memory manifest, summary views |
| `proposal list` | fast | current registry or lifecycle batch fallback |
| `decision status PROP` | targeted | schema preflight and one proposal source set |
| `project progress` | fast | one vertical state, definition, declared coverage batch |
| untargeted `context small` | fast | current compact views, no full decision index |
| targeted `context small` | targeted | compact views plus one decision-context index build/query |
| `next` | fast | one shared read context and bounded gap/remediation evaluation |
| `validate` | deep | complete structural and semantic validation once |
| `project freshness` | deep | complete dependency graph once |
| migration plan/apply preflight | deep/targeted | operation-specific complete checks |

Fast payloads include:

```yaml
verification:
  validation: not_run | fast_checked | current | stale | unknown
  freshness: not_run | fast_checked | current | stale | missing | unknown
  source: canonical | registry | vertical_memory | canonical_fallback
```

### Registry Bundle Contract

Owned paths:

```text
.p2p/registries/manifest.yml
.p2p/registries/proposals.yml
.p2p/registries/decisions.yml
.p2p/registries/changes.yml
.p2p/registries/choices.yml
.p2p/registries/relations.yml
.p2p/registries/artifacts.yml
.p2p/registries/readiness.yml
```

Manifest shape:

```yaml
registry_bundle:
  manifest_version: 1
  generator_contract_version: registry-bundle-v1
  source_catalog_policy_version: registry-sources-v1
  source_fingerprint:
    algorithm: sha256
    value: "..."
  source_scopes:
    proposals: "..."
    decisions: "..."
    changes: "..."
    choices: "..."
    readiness: "..."
  outputs:
    proposals.yml:
      sha256: "..."
      records: 102
    decisions.yml:
      sha256: "..."
      records: 102
  owned_paths: []
```

The source catalog enumerates only files that affect registry records. A fast
status hashes selected source bytes but does not parse them into records. A
metadata table may avoid rehashing unchanged candidates in a persistent MCP
process, but file hash remains the verification identity.

Refresh renders all outputs in memory, includes the manifest candidate, and
commits the bundle with `AtomicMutationWriter`. The manifest is semantically the
generation commit marker, but atomic transaction semantics protect the whole
set.

### YAML Loader Strategy

Foundation helpers expose named loader contracts. The default implementation
uses `yaml.CSafeLoader` when available and `yaml.SafeLoader` otherwise. Unique
mapping constructors are installed on matching C and Python loader subclasses.

No caller uses `yaml.load` without an explicit project-owned loader contract.
Migration owner-input tags and any specialized constructors remain isolated.
The implementation audit classifies each existing `safe_load` call before
mechanical replacement.

## Block B Design

### Owned Artifact Layout

```text
.p2p/project/vertical-memory/
  manifest.yml
  project.yml
  sections/
    <section-id>.yml
```

The directory is derived. It is excluded from canonical-source enumeration and
included as one output node in derived freshness. The section filename uses the
validated vertical section ID and cannot be supplied as an arbitrary path.

### Vertical Memory Manifest

```yaml
vertical_project_memory:
  manifest_version: 1
  generator_contract_version: vertical-project-memory-v1
  authority_policy_version: proposal-lifecycle-authority-v1
  source_catalog_version: vertical-memory-sources-v1
  vertical:
    id: software_project
    version: "1"
    checksum: "..."
  source_fingerprint:
    algorithm: sha256
    value: "..."
  source_scopes:
    project_definition: "..."
    project_questions: "..."
    proposals: "..."
    decisions: "..."
    declared_coverage: "..."
    relations: "..."
    choices_conflicts: "..."
  generation:
    mode: full | incremental
    rebuilt_sections: []
  outputs:
    project.yml: "..."
    sections/product_scope.yml: "..."
  owned_paths: []
```

Generation mode and rebuilt-section IDs are diagnostic metadata. They must not
change semantic project or section content. If complete byte idempotence would
be broken by recording the last mode, the builder records stable semantic mode
`materialized` and returns execution mode only in the operation result. The
implementation must choose byte idempotence over persisting observation data.

### Aggregate Project Record

```yaml
vertical_project:
  schema_version: 1
  vertical_id: software_project
  vertical_version: "1"
  sections:
    - id: product_scope
      required: true
      priority: 20
      path: sections/product_scope.yml
      state: current
      definition_status: complete
      active_contributions: 8
      historical_contributions: 2
      declared_evidence: 5
      unresolved_conflicts: 0
      open_questions: 1
      open_blockers: 0
  active_proposals: []
  historical_proposals: []
  unmapped_active_proposals: []
  diagnostics: []
```

The aggregate references sections and contains bounded IDs and counts. It does
not duplicate complete contribution bodies.

### Section Record

```yaml
vertical_section_memory:
  schema_version: 1
  vertical_id: software_project
  vertical_version: "1"
  section:
    id: product_scope
    title: Product Scope
    required: true
    priority: 20
  definition:
    status: complete
    fields: []
    assumptions: []
    open_questions: []
    blockers: []
    source: .p2p/project/definition.yml
    source_sha256: "..."
  active_contributions:
    - contribution_id: "..."
      proposal_id: PROP-100
      head_event_id: PDE-PROP-100-001
      authority: accepted_proposal_decision
      activation: active
      kind: decision | constraint | rationale | goal | non_goal | acceptance
      text: "..."
      text_sha256: "..."
      source_path: .p2p/proposals/PROP-100-example/decision.md
      source_sha256: "..."
      fragment_id: decision:reason:1
      lineage: {}
  historical_contributions: []
  declared_evidence:
    - proposal_id: PROP-100
      coverage_path: .p2p/proposals/PROP-100-example/vertical-coverage.yml
      confidence: owner_confirmed
  heuristic_suggestions: []
  conflicts: []
  diagnostics: []
```

Contribution IDs reuse decision-context stable record/evidence identity where a
matching record exists. New vertical-memory-only identities must be a stable
hash of vertical ID, section ID, owner ID, semantic slot, and source fragment
identity, never list position or line number.

### Compactness And Access Contract

`text` contains the smallest exact material fragment that carries the decision,
constraint, rationale, goal, non-goal, or acceptance fact. It is not a copy of
the complete proposal, decision artifact, or attachment. The source path,
fragment identity, and digests provide access to complete canonical evidence
when needed.

Section files may repeat a compact contribution only when explicit declared
coverage places the same authority in multiple sections. Every occurrence keeps
the same authority identity and adds section applicability; it does not create a
new decision. Aggregate `project.yml` stores counts and bounded IDs, not bodies.
Vertical memory never embeds decision-index postings, readiness gaps, next
actions, publication prose, or software-spec content.

Public list-bearing reads are projections over the complete derived files. They
return deterministic pages with `total`, `returned`, `truncated`, and a stable
cursor derived from semantic identity. Historical contributions are excluded by
default unless `--include-history` is supplied. Context assembly applies its own
stricter computation and byte budgets.

### Source And Selection Pipeline

Full generation performs:

1. Capture active vertical, lock, pack, definition, questions, and permissions.
2. Capture one lifecycle map.
3. Build one decision-context index from captured sources, or consume a derived
   index only after its contract and source fingerprint match those captures.
4. Resolve declared proposal-to-section relations.
5. Select active proposal decision and constraint records according to current
   authority and proposal binding.
6. Attach explicit rationale, lineage, conflict, choice, assumption, blocker,
   and question evidence.
7. Place valid declared contributions into section candidates.
8. Place non-active contributions into section history only when prior declared
   coverage or explicit topology identifies the section.
9. Place active proposals without valid declared coverage in the aggregate
   unmapped set.
10. Build every section, aggregate record, manifest, and output digest.

No stage infers an owner decision from wording. If two active contributions are
semantically different but have no explicit conflict assertion, both remain
visible. Deterministic lexical similarity may emit an advisory diagnostic only
if a versioned policy is later defined; it cannot resolve or suppress either.
Registries and materialized decision-context artifacts are accelerators only.
When their identity does not match the captured authority sources, the builder
uses canonical in-memory construction or returns an explicit unavailable result.

### Impact Classification

The impact classifier receives exact changed paths and optional typed decision
operation data. It produces:

```python
VerticalMemoryImpact(
    source_scopes=frozenset[str],
    section_ids=frozenset[str],
    aggregate_changed=True,
    full_rebuild=False,
    reasons=tuple[str],
)
```

| Change | Required impact |
| --- | --- |
| active vertical, lock, pack, profile, modules | full rebuild |
| section definition field/status | exact section plus aggregate |
| section assumption/blocker/question | exact section plus aggregate |
| proposal content affecting extracted records | all declared sections for proposal plus aggregate |
| decision authority/head/binding | all declared sections for proposal plus aggregate |
| vertical coverage | previous and new sections plus aggregate/unmapped |
| explicit relation or conflict | all exact related sections, otherwise full rebuild |
| project choice | sections reached by explicit active topology, otherwise aggregate and safe broad rebuild |
| registry-only representation change | no impact when canonical semantic inputs are unchanged |
| publication, software spec, Work implementation state | no impact unless cataloged project intent explicitly changes |

When the current valid projection cannot prove previous section membership, the
classifier chooses full rebuild.

### Full And Incremental Equivalence

There is one pure section renderer. Full and incremental builders differ only
in how they choose which section inputs to recalculate. Incremental generation:

1. validates the current manifest and every reused output digest;
2. classifies impact;
3. captures all aggregate source identities needed for the new manifest;
4. rebuilds affected sections with the shared renderer;
5. reuses validated unchanged section bytes;
6. rebuilds aggregate project record and manifest;
7. compares the complete candidate against a full build in tests.

Production does not run a second full build merely to prove equivalence. The
test matrix covers every impact class and randomized sequences.

### Atomic Generation

The service renders candidates before acquiring the mutation lock. It then:

- creates source preconditions for every canonical input used by the build;
- includes every owned current and candidate output as a transaction target;
- deletes stale owned outputs only through candidate `None` entries;
- validates candidate schema and internal references against a candidate
  workspace view;
- commits with `AtomicMutationWriter`;
- returns changed paths, affected sections, source fingerprint, and status.

If canonical sources changed between render and commit, the transaction fails
without replacing the previous generation. The caller may recompute once.

### Post-Commit Derived Refresh

Only these canonical operations are initial integration targets:

- proposal decision apply for accepted, revoked, reinstated, superseded, split,
  and merged events;
- proposal vertical coverage apply;
- project definition apply;
- project readiness question convergence apply;
- active vertical selection or reconciliation.

After canonical commit, the facade considers an independent incremental refresh
with the operation's exact changed paths and semantic operation. It applies the
candidate only when the previous generation is current and compatible and the
impact classifier proves that an incremental/no-op result is sufficient. If the
generation is missing, invalid, unsupported, or requires a full rebuild, it
reports stale/not-applicable and recommends explicit `p2p project refresh`.
The canonical result is already final. The public result gains additive
derived-state detail:

```yaml
derived_updates:
  vertical_project_memory:
    status: updated | unchanged | stale | failed | not_applicable
    sections: []
    command: p2p project refresh
    diagnostic: ""
```

A derived refresh failure returns canonical success plus `failed`; it never
changes the canonical status to failure. A vertical switch normally reports
`stale` because its impact requires a full rebuild. Operations not yet integrated
rely on fingerprint-based stale detection and explicit refresh.

### Status And Fallback

`VerticalProjectMemoryService.status()`:

1. reads and validates manifest shape/version;
2. verifies output existence and digests;
3. computes current source fingerprints without rendering section semantics;
4. returns current, stale, missing, invalid, or unsupported with reasons.

`WorkspaceReadContext.vertical_memory()` behavior:

| Materialized state | Authority-sensitive caller | Display-only caller |
| --- | --- | --- |
| current | use materialized | use materialized |
| stale | build canonical candidate in memory | caller may request stale last-known data, labeled stale |
| missing | build canonical candidate in memory | build candidate or report missing |
| invalid/unsupported | build candidate only if canonical inputs validate; otherwise fail | report invalid/unsupported |
| fallback build failure | fail explicitly | report unavailable; never invent data |

In-memory fallback returns the same typed view as materialized files and writes
nothing.

## Block C Design

### Dependency Graph Without Cycles

```text
canonical sources
  -> lifecycle + decision context + vertical definition
  -> vertical project memory
  -> project progress/readiness
  -> next actions/context/rendering
  -> visible export/publication
```

Vertical memory stores definition/question facts but not computed readiness
gaps or next actions. Readiness stores or returns gap classification separately.
This prevents `vertical memory -> readiness -> vertical memory` cycles.

### Readiness Adapter

`ProjectReadinessSnapshotBuilder` gains a constructor from
`VerticalProjectMemoryView`. It maps:

- section definition state and required fields;
- active declared proposal evidence;
- heuristic suggestions as informational only;
- assumptions, blockers, and questions;
- projection diagnostics and unmapped active proposals;
- source hashes and policy versions.

`ProjectReadinessGapService` remains the classifier. Golden tests compare the
existing canonical-source snapshot and the new projection-backed snapshot
during transition. Once parity passes, the old source scan becomes the canonical
fallback builder rather than the ordinary materialized path.

Readiness incremental optimization may classify only affected section snapshots
internally, but the returned result and stable gap ordering must equal a full
classification.

### Context Packet

Untargeted small context uses:

- schema preflight;
- registry and vertical-memory fast status;
- aggregate vertical project record;
- bounded section summaries ordered by required status, open blockers, open
  questions, and vertical priority;
- projection-backed readiness result;
- bounded next actions from the same read context.

It does not call full validation, full freshness, publication status, software
spec status, or full decision-context construction.

Targeted proposal context additionally builds or consumes decision context and
retrieves nearby evidence. It identifies vertical sections related to the target
and frames hits inside current section direction. Existing token and byte
budgets remain authoritative.

### Next Actions

`NextActionService` no longer owns callbacks that can freely rebuild global
state. Its query input becomes a typed snapshot assembled by the read context:

```python
NextActionInputs(
    schema_preflight,
    fast_freshness,
    proposal_lifecycles,
    decision_context_or_compact_topology,
    readiness,
    change_statuses,
    intake_statuses,
    curated_actions,
)
```

Untargeted next actions may use compact active choice/change/remediation topology
from vertical memory and registries. Detailed proposal impact remains targeted
and receives the one shared freshness/lifecycle snapshot.

If vertical memory is stale and no canonical fallback is available, one stable
refresh action is emitted and dependent section actions are suppressed.

### Project Rendering

Existing `ProjectStateService.refresh()` remains the owner of existing project
projection paths. It consumes current or in-memory vertical memory and renders:

- overview from active vertical and current section directions;
- problem and scope grouped by vertical section;
- decisions map from active decision contributions with historical references;
- existing feature directories for compatibility;
- projection manifest with vertical-memory source fingerprint.

The renderer keeps one H1 per document where relevant, deterministic ordering,
and compact references. It never claims implementation from Change Set, Work,
spec, or repository code presence.

Visible export and publication continue to consume project projections through
their current explicit lifecycle. Publication approval remains owner-controlled.

## Block X Design

Block X records a reproducible evaluation document in this feature directory
after implementation. The exact file is:

```text
specs/features/vertical-aware-project-memory-performance-and-incremental-projection/persistence-evaluation.md
```

The document contains:

- source revision and package import path;
- hardware, OS, filesystem, and Python versions;
- dataset sizes and artifact counts;
- cold CLI median and p95;
- warm MCP first, steady-state, post-mutation, and concurrent results;
- structural operation counts;
- registry and vertical-memory file sizes;
- full and incremental rebuild times;
- peak memory;
- failed targets and bottleneck attribution;
- outcome `filesystem_sufficient` or `persistent_index_feature_required`;
- evidence supporting the outcome.

No cache or database prototype is required to select either outcome.
The current repository is measured through read-only operations, canonical
in-memory candidates, or a disposable copy/scratch destination. The persistent
workspace refresh in Block M occurs only after the final implementation gate and
owner authorization, so Block X and Block M do not depend on one another
circularly.

## Public API And Compatibility

### Additive Core Types

- `WorkspaceReadContext`
- `WorkspaceDocumentStore`
- `CapturedDocument`
- `ReadOperationCounters`
- `WorkspaceSchemaPreflight`
- `VerticalReadState`
- `RegistryBundleManifest`
- `VerticalProjectMemoryManifest`
- `VerticalProjectMemoryView`
- `VerticalSectionMemory`
- `VerticalMemoryImpact`
- `VerticalMemoryStatus`
- `DerivedUpdateResult`
- `FastFreshnessSummary`

Exact module placement follows existing boundaries: core immutable contracts in
`core`, source and transaction adapters in `services` or `foundation`, and
public orchestration in `storage/filesystem.py` until a later facade extraction.

### CLI

Add:

```text
p2p project memory status [--format text|json]
p2p project memory show [--section SECTION-ID] [--include-history]
                        [--limit N] [--cursor TOKEN] [--format text|json]
```

Extend without renaming:

```text
p2p project refresh
p2p status
p2p proposal list
p2p project progress
p2p context
p2p next
p2p registry status
p2p registry refresh
```

Fast commands add verification/source metadata only in structured output.
Existing text remains recognizable, with explicit `not_run` or stale labels.

### MCP

Add read-only tools equivalent to project-memory status and show. If a derived
refresh MCP tool is added, it must be explicitly write-safe, route to the same
`p2p project refresh` service, honor runtime/schema write preflight, and return
changed paths. No read tool may trigger refresh.

Existing context, next, status, readiness, and project tools receive additive
fields only after CLI behavior and serializers are stable.

## Performance And Observability

Every read context exposes non-public or debug counters suitable for tests:

```yaml
discovery_passes: {}
source_reads: {}
source_hashes: {}
yaml_parses: {}
schema_preflights: 0
schema_deep_validations: 0
ledger_parses: {}
vertical_pack_loads: {}
provider_calls: {}
provider_cache_hits: {}
canonical_fallbacks: {}
```

Public CLI does not print counters by default. Benchmark helpers and tests may
serialize them. Tests assert upper bounds such as:

- fast proposal list: one registry status plus zero or one lifecycle batch;
- lifecycle batch: at most `N` ledger parses for `N` proposals;
- progress: one active vertical and one pack load;
- untargeted context: zero deep validation, zero deep freshness, zero full
  decision-context build;
- targeted context: at most one decision-context build;
- next actions inside context: zero additional global provider builds.

## Test Strategy

### Focused Tests

- read context laziness, memoization, immutability, and retry;
- document capture and loader-contract isolation;
- schema preflight versus deep findings;
- lifecycle single/batch parity and scale;
- vertical declared/heuristic batch parity and scale;
- registry manifest, same-count staleness, atomicity, and fallback;
- YAML C/Python semantic parity;
- vertical-memory schema, authority selection, mapping, history, and conflicts;
- impact classification and full/incremental byte equivalence;
- status/fallback and failure injection;
- readiness parity and independent axes;
- context and next-action provider counts;
- vertical-first rendering and traceability.

### Scale Tests

- 100 proposals with rich artifacts and multi-event ledgers;
- 1,000 proposals with deterministic mixed lifecycle and coverage;
- 10,000 minimal proposals for structural complexity and bounded payload tests;
- reversed and randomized enumeration;
- unrelated proposal additions;
- repeated mutation and incremental refresh sequences;
- concurrent MCP readers with one governed writer.

### Public And Package Tests

- CLI text and JSON;
- MCP schemas and payload parity;
- docs and generated instruction drift;
- Python 3.11 compatibility;
- editable source tests;
- wheel/sdist installed-artifact smoke tests that explicitly prove import path;
- public and full suites.

## Rollout And Compatibility

1. Ship Block A with existing read-model behavior and no vertical-memory
   dependency.
2. Add Block B artifact support as optional derived state. Missing memory uses
   canonical fallback and does not invalidate a compatible workspace.
3. Generate vertical memory through explicit project refresh and prove current
   repository output before switching ordinary consumers.
4. Switch Block C consumers one at a time behind parity tests.
5. Retain canonical fallback through the final gate.
6. Run Block X and record the persistence outcome using fixtures and read-only
   or scratch current-repository evidence.
7. After the final gate and owner authorization, run Block M to align derived
   state in the current repository through supported commands.

No workspace schema bump is required for an optional rebuildable output. A
future release that makes the artifact mandatory, changes canonical authority,
or removes fallback must reassess schema and migration requirements.

Local package builds and isolated installs in the test strategy are verification
artifacts only. They do not imply or authorize commit, tag, push, release, or
package publication.

## Alternatives Rejected For This Feature

### Global `lru_cache`

Rejected as the primary solution because separate CLI processes do not share it
and unkeyed mutable-file caches become stale.

### Eager Workspace Snapshot

Rejected because a proposal list must not build vertical, readiness, freshness,
publication, and decision-index state.

### Rebuild Everything After Every Write

Rejected because governance writes would inherit publication, readiness, and
projection latency and failure modes.

### Read-Time Persistent Rebuild

Rejected because reads must remain side-effect free and transparent.

### Use Rendered Narrative As Project State

Rejected because prose is difficult to invalidate, compare, and use as
readiness authority.

### SQLite Or Graph Database

Deferred to Block X evidence. Current raw read and hash costs are small relative
to repeated parsing and global computation.

## Traceability Rule

The implementation matrix must be updated at every slice exit with direct code,
test, benchmark, and artifact evidence. Final traceability review supplements
slice evidence; it does not recreate missing evidence after implementation.
