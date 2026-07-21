# Design - Multilingual Human Project Publication And Editorial Curation

## Requirements Covered

- A-R001..A-R010
- B-R001..B-R018
- C-R001..C-R018
- D-R001..D-R010
- E-R001..E-R012
- F-R001..F-R010
- G-R001..G-R020
- N001..N014
- X001..X024
- AC001..AC024

## Design Summary

Retain the implemented deterministic publication pipeline, but replace its
single unsuffixed, proposal-oriented curation contract with:

1. a shared, complete, vertical-aware evidence index;
2. an explicit language/output-name edition identity;
3. a structured curator-authored project model and evidence accounting;
4. one autonomous reader document per language edition;
5. edition-scoped validation, rendering, review, and freshness;
6. concise generated curator skills with progressively loaded references.

The design deliberately separates three representations:

| Representation | Purpose | Reader-facing | Authority |
| --- | --- | --- | --- |
| complete export/evidence index | exhaustive research and audit input | no | derived from `.p2p` |
| publication model/accounting | semantic synthesis and traceability | no | derived curator output |
| edition Markdown/PDF | autonomous project explanation | yes | derived publication |

## Key Decisions

### D001 - Correct PROP-099 Instead Of Replacing Its Pipeline

Keep prepare, import, validate, render, review, status, hash provenance, optional
PDF, CLI, and MCP boundaries. Change their artifact and editorial contracts.

Rationale: the stage separation is sound. The defect is that the current packet,
skill, validation rules, and fixed paths steer curation toward governance
summaries and prevent multilingual coexistence.

### D002 - One Project Scope, Independent Language Editions

The feature supports multiple language editions of the same project, not
multiple purpose/audience documents. Every edition uses the same evidence-index
contract and vertical completeness questions. The curator still authors a
language-bound model because claims and headings are linguistic artifacts, but
edition drift is compared against the same shared source fingerprint.

Rationale: translation is not byte substitution. Each language needs separate
validation and owner review, while project scope must remain invariant.

### D003 - English Default, Normalized BCP 47 Identity

Use `en` as the default. Normalize tags before path resolution. Preserve a
canonical tag for metadata and a lowercase path tag for filenames. Support
explicit compatibility aliases `eng -> en` and `ita -> it`.

Rationale: BCP 47 gives a standard identity and avoids inventing a filename-only
language scheme. Three-letter user input remains convenient while canonical
paths stay predictable.

### D004 - Safe Output Name Plus Language Suffix

Use `edition_key = <output-name>-<path-language>`. The default is `project-en`.
Final reader files remain directly visible under `outputs/latest`; internal
edition metadata lives in a namespaced directory.

Rationale: a user can produce `outputxyz-en.pdf` and `outputxyz-it.pdf` without
collisions, while tooling receives one stable metadata root per edition.

### D005 - Complete Evidence Index, Not Embedded Full Export

Generate a shared `publication-evidence.yml` containing stable evidence entries
and complete source accounting. Each entry carries a complete normalized
semantic payload or a content-complete source locator; a lossy generated summary
is never the only representation. Keep `project.md` by path/hash, but do not
fence and embed its 20k+ lines in every packet.

Rationale: embedding the export consumes context, duplicates bytes, and makes
its proposal-oriented sequence look like the desired publication structure.
An index allows complete traversal, progressive disclosure, and explicit
accounting without first-N truncation.

### D006 - Use Vertical Memory As The Primary Structured Input

Build the evidence index from one request-scoped snapshot and the current
vertical-memory/registry/project-state providers. Add source records that are
not represented in vertical memory, especially active unmapped evidence,
project questions/assumptions, contribution records, and process-only records.

Rationale: the recently implemented vertical memory already classifies active
and historical contributions by section. Reusing it avoids another full
proposal scan and aligns publication with readiness/project projection.

### D007 - Governance Selects Sources But Is Not Reader Content

Lifecycle authority classifies evidence as active, historical, or process-only.
The publication model and prose use project concepts. They do not expose
proposal status, decision events, Change Sets, Work, readiness, or publication
pipeline mechanics as upstream provenance. When proposals, decisions,
governance, or lifecycle behavior are themselves supported capabilities of the
project being documented, the curator explains those concepts as subject matter
for a new reader without leaking internal IDs or source status tables.

Rationale: governance is necessary for correctness but irrelevant to the final
reader. This also avoids the false inference that proposal acceptance means a
feature was implemented.

### D008 - Structured Model And Complete Accounting Are Import Preconditions

Require three curator candidates: Markdown, project model YAML, and evidence
accounting YAML. Import validates referential completeness before committing
them as one edition revision.

Rationale: prose alone cannot prove that all evidence was considered or show
which claims it supports. Sidecars preserve rigorous traceability without
polluting the reader document.

### D009 - Adaptive Outline Through Vertical Questions

Vertical sections generate reader questions and completeness obligations. They
do not become a fixed chapter list. The model records whether each applicable
vertical obligation is covered, combined with another chapter, unsupported, or
not applicable.

Rationale: a software product and a board game need different explanations.
Even two projects in one vertical can require different narrative order.

### D010 - Exact Candidate Paths

Prepare declares the candidate triplet under
`drafts/project-publication/<edition-key>.*`. The skill writes there. Import is
the only path into `outputs/latest` edition artifacts.

Rationale: this removes the current contradiction where the skill says to write
the canonical output but import rejects the canonical path.

### D011 - Traceability Sidecars By Default

Do not require proposal IDs, source paths, hashes, or `.p2p` authority boilerplate
in reader prose. Keep all claim/evidence/source links in model, accounting, and
manifest files. A technical appendix is not enabled in this feature.

Rationale: the final reader should understand the project without knowledge of
P2P. Technical traceability remains available to maintainers and agents.

### D012 - Deterministic Contribution Shares Only

Prepare computes contributor shares from current explicitly recorded
contribution records. Allocate integer basis points with largest remainder,
including unattributed records in the denominator. The chapter is optional and
contains a mandatory methodological limitation.

Rationale: deterministic record shares are reproducible. Effort, value,
ownership, and IP cannot be inferred from the available data.

### D013 - Deterministic Validation Does Not Claim Editorial Proof

The validator verifies paths, hashes, schemas, referential completeness,
structural Markdown rules, and detectable internal workflow leakage. Language
quality, factual adequacy, vertical fit, and prose quality remain rubric-driven
agent/owner evaluation.

Rationale: a regex cannot prove semantic quality. The implementation should be
strict where truth is machine-checkable and explicit where it is not.

### D014 - Edition-Scoped Manifests With A Shared Catalog

Use one per-edition manifest and one stable shared catalog. The per-edition
manifest is the commit marker for staged multi-file imports. Shared evidence
hash changes stale all editions; local content changes stale only descendants in
that edition.

Rationale: a single monolithic manifest creates unnecessary cross-edition write
contention and makes atomic stage ownership less clear.

### D015 - Derived Contract Upgrade, No Workspace Migration

Call the new evidence/model/profile/manifest/template contracts version 2 where
they replace current publication-v1 behavior. Leave workspace schema v3 intact.
Detect old unsuffixed output as legacy. Do not copy old publication approval.

Rationale: publication files are regenerated derived outputs, not canonical
workspace records. A workspace schema migration would misclassify the change.

### D016 - Default-English Compatibility Aliases Are Outputs Only

During a documented compatibility window, the default `project-en` edition may
refresh `project.curated.md` and `project.pdf` aliases after successful writes.
Never read those aliases as stage inputs. Never write aliases for another
edition.

Rationale: current integrations can continue finding the familiar final files
while all status/provenance authority moves to the versioned edition contract.

### D017 - Skill Uses Progressive Disclosure

Generate a concise `SKILL.md` and one-level references:

```text
p2p-project-curator/
  SKILL.md
  references/editorial-workflow.md
  references/model-and-evidence-contract.md
  references/vertical-interpretation.md
  references/editorial-rubric.md
```

Rationale: the core skill should be cheap to load. Detailed schemas and rubric
guidance are needed only while executing their respective steps.

### D018 - Owner Review Is Per Edition And Outside Governance

Keep owner review because language quality and publishability are not fully
deterministic. Bind review to the selected edition's complete current hash set.
Do not expose review through MCP in this feature.

Rationale: publication approval is useful, but it must not be confused with a
proposal/project governance decision or inherited by another translation.

## Artifact Layout

```text
outputs/latest/
  project.md                         # complete existing audit export
  publication-evidence.yml          # shared evidence index v2
  publications.yml                  # edition catalog v2
  project-en.md                      # reader document
  project-en.pdf                     # reader PDF
  project-it.md
  project-it.pdf
  publications/
    project-en/
      profile.yml
      curator-input.md
      manifest.yml
      project-model.yml
      evidence-accounting.yml
      validation.yml
      review.yml
    project-it/
      ...
drafts/project-publication/
  project-en.md
  project-en.model.yml
  project-en.evidence.yml
```

## Core Contracts

### Edition Identity

```python
@dataclass(frozen=True)
class PublicationEdition:
    output_name: str
    language: str
    path_language: str
    edition_key: str
```

The parser performs all validation before path construction. Service methods
accept this value, not independent unvalidated strings.

### Publication Paths

```python
@dataclass(frozen=True)
class PublicationEditionPaths:
    edition: PublicationEdition
    metadata_dir: Path
    profile: Path
    curator_input: Path
    manifest: Path
    model: Path
    evidence_accounting: Path
    validation: Path
    review: Path
    markdown: Path
    pdf: Path
    candidate_markdown: Path
    candidate_model: Path
    candidate_evidence: Path
```

All fields are produced by one resolver and checked to remain under their
declared roots after symlink-aware resolution.

### Shared Evidence Index V2

Illustrative shape:

```yaml
schema_version: 2
generator: publication-evidence-v2
source_fingerprint_sha256: "..."
vertical:
  id: software_project
  version: 1.0.0
  available: true
source_export:
  path: outputs/latest/project.md
  sha256: "..."
sources:
  - path: .p2p/project/definition.yml
    sha256: "..."
entries:
  - id: EVD-...
    kind: project_definition
    authority_class: active
    editorial_class: project_evidence
    vertical_sections: [vision_objectives]
    source_path: .p2p/project/definition.yml
    source_selector: yaml:/sections/vision_objectives
    semantic_sha256: "..."
    content_mode: inline_complete
    payload:
      objective: "..."
contributions:
  policy_version: recorded-contribution-share-v1
  denominator: 10
  rows:
    - author: mrjungle
      count: 9
      basis_points: 9000
      percentage: "90.00"
```

Evidence IDs derive from kind, canonical source path/selector, and semantic
content identity, not list position or filesystem order. `content_mode` may be
`inline_complete` or `source_complete`. The latter must provide enough selector,
encoding, and hash data to retrieve the entire evidence unit; it cannot point to
an unexplained truncation.

### Profile V2

```yaml
schema_version: 2
profile_id: human-project-publication-v2
edition:
  output_name: project
  language: en
  path_language: en
  key: project-en
reader:
  knowledge_of_p2p: none
  audience_variant: false
editorial:
  structure: vertical_adaptive
  traceability_in_body: false
  contributions: auto
render:
  theme: neutral-v1
```

The profile no longer contains `project_default`, fixed `mixed` audience, or a
generic `include_appendix` boolean.

### Publication Model V2

Illustrative shape:

```yaml
schema_version: 2
edition:
  key: project-en
  language: en
bindings:
  curator_packet_sha256: "..."
  evidence_index_sha256: "..."
  source_export_sha256: "..."
project:
  title: P2P Engine
  thesis: "..."
  vertical_id: software_project
reader_questions:
  - id: RQ-001
    question: "What problem does the project solve?"
    answered_by: [CLM-001]
claims:
  - id: CLM-001
    statement: "..."
    evidence_ids: [EVD-...]
    vertical_sections: [problem_users]
outline:
  - id: SEC-001
    role: project_overview
    heading: Project Overview
    claim_ids: [CLM-001]
vertical_coverage:
  - section_id: problem_users
    disposition: covered
    outline_ids: [SEC-001]
editorial_assessment:
  rubric_version: publication-editorial-rubric-v2
  results: []
```

Claim IDs and evidence IDs are internal and never need to appear in final prose.

### Evidence Accounting V2

```yaml
schema_version: 2
edition_key: project-en
bindings:
  model_sha256: "..."
  evidence_index_sha256: "..."
evidence:
  - evidence_id: EVD-...
    disposition: used
    claim_ids: [CLM-001]
    reason: Supports the project objective.
```

Import compares the exact set of evidence IDs. Process-only entries may be
pre-populated by prepare but remain present in the final accounting.

### Manifest And Catalog V2

The edition manifest records:

- edition identity and all contract versions;
- shared source and evidence fingerprints;
- profile and packet hashes;
- imported candidate source paths and hashes;
- model, accounting, Markdown, validation, PDF, and review stage hashes;
- compatibility alias hashes where applicable;
- generator/validator/renderer/template IDs;
- interruption/incomplete diagnostics.

The shared catalog records only stable edition discovery and summarized status.
It does not duplicate complete per-edition provenance.

## Evidence Construction

### Source Snapshot

`ProjectPublicationEvidenceService` receives or creates one
`WorkspaceReadContext`. It requests:

- workspace schema preflight, not deep status;
- proposal lifecycle map once;
- registry bundle once;
- active vertical state once;
- vertical project memory once;
- project definition/questions/assumptions snapshot once;
- accepted/current cross-cutting sources not represented in vertical memory;
- contribution records once;
- complete export provenance once.

It must not invoke full freshness, repeated vertical matching, or one lifecycle
read per proposal.

### Entry Classification

Classification happens in two layers:

1. deterministic authority/editorial eligibility from source state;
2. curator disposition in evidence accounting.

Deterministic classification does not summarize away contradictions. It exposes
them with stable IDs. Curator accounting cannot promote historical/process-only
evidence into a current claim without an explicit validation diagnostic.

### Vertical Completeness

Each required applicable vertical section becomes one or more reader questions.
The model may combine several questions in one chapter. Missing evidence remains
an internal model gap and may become a plainly worded project uncertainty if it
matters to the reader.

## Curator Workflow

The generated skill executes this order:

1. Verify packet, edition, profile, source, and evidence hashes.
2. Read the active vertical interpretation reference.
3. Traverse every evidence-index entry in vertical groups; open referenced
   source material when the index is insufficient.
4. Separate project substance from process-only/historical context.
5. Draft reader questions and model claims with evidence links.
6. Account for every evidence entry.
7. Design an adaptive outline in the requested language.
8. Write the standalone reader Markdown without internal IDs or workflow prose.
9. Apply contribution data exactly when profile policy requires it.
10. Run autonomy, unsupported-claim, vertical, language, and governance-noise
    rubric checks.
11. Write the exact candidate triplet and stop; do not import or approve it.

The skill may not depend on WaveKit, this repository's neighboring projects, or
any external product identity unless present in allowed evidence.

## Contribution Share Algorithm

1. Select explicitly recorded contribution records attached to current
   authoritative project evidence.
2. Normalize author with Unicode NFC and collapsed surrounding/internal
   whitespace; blank becomes `Unattributed`.
3. Do not casefold or alias identities for aggregation.
4. Count records per display identity.
5. Compute exact quota `count * 10000 / total` basis points.
6. Assign floors, then distribute remaining basis points by descending
   fractional remainder and normalized display-name order.
7. Sort output by descending count then normalized display name.
8. Emit count, integer basis points, and two-decimal percentage string.

The packet supplies this computed table. The curator does not recalculate it.

## Import Transaction

Import performs:

1. resolve and validate edition/candidate paths;
2. verify current packet and shared evidence bindings;
3. parse model/accounting with duplicate-key-safe YAML;
4. validate schemas, identity, complete evidence set, claim links, and profile
   contribution policy;
5. capture current target manifest revision/hash;
6. stage model, accounting, and Markdown in the edition metadata filesystem;
7. atomically replace each target;
8. atomically write the manifest last as the commit marker;
9. refresh the shared catalog from committed manifests;
10. refresh default-English compatibility Markdown alias when enabled;
11. on failure, remove temporary files and leave the old committed manifest
    untouched; status reports any uncommitted target mismatch as incomplete.

No read operation repairs an interrupted import.

## Freshness Graph

```text
workspace/project snapshot
  -> project.md + publication-evidence.yml
  -> edition profile + curator packet
  -> model + evidence accounting + Markdown
  -> validation
  -> PDF
  -> review
```

Shared-source drift stales all descendants in all editions. A profile change
stales the selected edition from packet onward. Model/accounting/Markdown changes
stale validation onward. Validation changes stale PDF/review. PDF changes stale
review. Review never affects earlier stages.

## Validation Layers

### Deterministic Errors

- unsafe or wrong edition paths;
- unsupported contract versions;
- stale/missing hash bindings;
- malformed/duplicate-key YAML;
- incomplete evidence accounting;
- broken model claims/evidence/outline references;
- contribution table mismatch;
- empty Markdown, invalid UTF-8, H1 count, unclosed fences;
- internal proposal/decision/Change Set/Work IDs in reader prose, while allowing
  the same generic concepts when they are evidenced project subject matter;
- manifest or edition identity mismatch.

### Heuristic Findings

- probable language mismatch;
- weak vertical framing;
- headings that mirror workflow/process artifacts;
- governance narration or readiness percentages;
- placeholder text;
- unusually imbalanced chapters;
- suspicious contribution wording;
- unsupported-claim risk inferred from model/prose mismatch.

### Editorial Rubric

An agent/owner evaluation records evidence and scores for:

- project autonomy;
- vertical coherence;
- evidence completeness/accounting;
- unsupported claims;
- governance-noise absence;
- language consistency;
- contribution accuracy;
- structure and readability;
- usefulness to a reader with no P2P knowledge.

Rubric scores are evaluation evidence, not deterministic validation status.

## Public Interface

### CLI

```bash
p2p project publish prepare \
  --language en \
  --output-name project \
  --contributions auto

p2p project publish import \
  drafts/project-publication/project-en.md \
  --model drafts/project-publication/project-en.model.yml \
  --evidence-accounting drafts/project-publication/project-en.evidence.yml \
  --language en \
  --output-name project

p2p project publish validate --language en --output-name project
p2p project publish render --language en --output-name project
p2p project publish review --language en --output-name project --status approved
p2p project publish status --language en --output-name project
p2p project publish list
```

All edition selectors default to `en`/`project`. Text and JSON include canonical
language and edition key. `list` is read-only.

### MCP

Retain existing publication tool names and add optional fields:

- `language`
- `output_name`
- `contributions` on prepare
- `model` and `evidence_accounting` on import

Add a read-only list tool if CLI list is public. Do not add MCP review.

### Workspace Facade

Facade methods accept keyword-only edition fields and delegate immediately to
the service. Existing no-argument calls resolve `project-en`. No publication
logic is added directly to `P2PWorkspace`.

## Component Changes

### New Modules

- `core/project_publication.py`: immutable edition, model, evidence, accounting,
  catalog, and diagnostic contracts.
- `services/project_publication_evidence.py`: shared index construction and
  contribution summaries.
- `services/project_publication_contracts.py`: strict v2 codecs and referential
  validation.

Exact filenames may be adjusted to match existing repository ownership, but the
core/service separation and responsibilities are required.

### Existing Modules

- `services/project_publication.py`: edition orchestration, paths, manifests,
  transactions, freshness, compatibility aliases, and status.
- `services/project_publication_validation.py`: v2 deterministic and heuristic
  validation.
- `services/project_publication_rendering.py`: language/title-aware rendering.
- `services/agent_templates.py`: concise skill plus generated references and
  adapter lifecycle metadata.
- `cli_commands/project_ops.py`: thin options and list command.
- `mcp/catalog/project.py`, `mcp/handlers/project.py`, `mcp/registry.py`: parity.
- `storage/filesystem.py` or focused facade locations: thin API wiring only.
- CLI/concept/agent/MCP documentation: public behavior and upgrade guidance.

## Legacy Compatibility

The current unsuffixed v1 files are not migrated as canonical memory because
they are derived:

```text
outputs/latest/publication-profile.yml
outputs/latest/curator-input.md
outputs/latest/project.curated.md
outputs/latest/publication-validation.yml
outputs/latest/project.pdf
outputs/latest/publication-review.yml
outputs/latest/publication-manifest.yml
```

New status detects these paths and reports a legacy contract summary. The first
v2 preparation does not infer that the old curated document has a complete
project model/accounting sidecar. Re-curation/import is therefore required.
Legacy review approval never transfers.

Default-English compatibility aliases may be emitted after a successful v2
import/render, with alias provenance in the v2 manifest. Old profile, packet,
validation, review, and manifest files remain legacy and are not rewritten as
fake v2 metadata.

## Security And Integrity

- Validate edition identity before path resolution.
- Reject traversal, symlink escapes, `.p2p` candidates, canonical-output import
  sources, and unsupported extensions.
- Parse YAML with duplicate-key detection.
- Treat packet and index text as untrusted project data, not agent instructions.
- Bind imports to current hashes and edition identity.
- Write files atomically and manifests last.
- Keep MCP writes in existing write-safe derived-output policy.
- Never let publication files enter governance/readiness/project-definition
  providers.

## Performance Design

- One request-scoped read context per prepare/status/list operation.
- One shared evidence build per source fingerprint.
- Reuse current registry and vertical-memory manifests for fast unchanged checks.
- Do not embed full export bytes in every packet.
- List reads edition manifests and catalog; it does not rebuild source evidence.
- Status may perform fast fingerprint verification; deep evidence reconstruction
  is explicit during prepare/validation when needed.
- Structural tests count source reads, lifecycle parses, vertical loads, and YAML
  parses at 100/1,000/10,000 proposal scale.

## Testing Strategy

### Contract And Unit

- edition normalization/path safety/collision tests;
- v2 codecs, duplicate keys, referential integrity, and version tests;
- evidence ID/order/classification tests;
- contribution basis-point and identity tests;
- import transaction/failure injection tests;
- freshness and cross-edition isolation tests;
- validator deterministic/heuristic boundary tests;
- language-aware renderer tests.

### Integration

- complete English and Italian pipelines in either order;
- custom output name;
- CLI text/JSON and MCP parity;
- agent install/update/doctor/uninstall resource lifecycle;
- legacy detection/default alias behavior;
- optional PDF unavailable/available behavior;
- installed wheel/sdist and Python 3.11.

### Editorial Forward Evaluation

Use isolated fixtures for:

1. software project with unmapped active and historical evidence;
2. board game with rules, components, players, setup, progression, and victory
   conditions;
3. custom/unknown vertical requiring generic framing;
4. unrelated-brand contamination trap.

Evaluate candidate model/accounting/document triples without exposing expected
wording. Record rubric evidence and defects. Deterministic tests validate
contracts; agent/owner review validates editorial usefulness.

## Rollout

1. Implement contracts and paths behind service defaults.
2. Add evidence/model/accounting and new packet.
3. update skill templates and forward-evaluate them.
4. switch import/validation/render/review to v2 edition state.
5. expose CLI/MCP and compatibility behavior.
6. pass source and installed-artifact gates.
7. separately preview repository alignment.
8. after owner confirmation, refresh generated agent resources and regenerate
   this repository's publication editions without modifying `.p2p` manually.

## Rejected Alternatives

### Rewrite `project.md` As The Reader Document

Rejected because `project.md` remains useful as a complete audit export and its
proposal-oriented form should not define final editorial structure.

### Keep One Unsuffixed Output And Translate In Place

Rejected because languages overwrite one another and approval/freshness cannot
be edition-specific.

### Put Traceability In A Mandatory Reader Appendix

Rejected for this feature because the owner explicitly wants a document for a
reader uninterested in upstream process. Sidecars preserve traceability.

### Infer Project Implementation From Change Sets Or Source Code

Rejected because P2P designs projects and does not know whether downstream work
is implemented, shipped, or discarded unless explicit project evidence says so.

### Deterministically Generate Final Prose

Rejected because vertical interpretation, synthesis, and autonomous narrative
require agentic/human editorial work. The CLI remains provider-independent.

### Add A Database Or Translation Dependency

Rejected because file-backed indexed state is sufficient, and model/translation
providers would expand scope without fixing the editorial contract.

### Migrate Workspace Schema v3 To v4

Rejected because all changed artifacts are derived publication contracts.
