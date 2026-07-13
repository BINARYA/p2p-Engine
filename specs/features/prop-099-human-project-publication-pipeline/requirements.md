# Requirements - PROP-099 Human Project Publication Pipeline

## Origin

- Source P2P proposal: `PROP-099 - Project Output Lifecycle and Retention Policy`
- Accepted direction: Human Project Publication Pipeline.
- Governance status at this revision: `accepted`, readiness `decision_ready`,
  score `100`, confidence `high`.
- Local implementation status: implemented in local repository code; see
  `implementation-note.md` for delivered files, command surface, and validation
  evidence.

This spec is local implementation planning. P2P governance state remains under
`.p2p/`; generated publication outputs are derived artifacts and must not become
source-of-truth memory.

## Scope

Prepare an end-to-end project publication pipeline that turns the complete
generated project export into one readable, human-oriented, vertical-aware
canonical project document.

The first slice must keep each stage independently reviewable:

```text
.p2p managed state
  -> p2p project export
  -> outputs/latest/project.md
  -> p2p project publish prepare
  -> outputs/latest/curator-input.md
  -> external agentic curation
  -> p2p project publish import <file>
  -> outputs/latest/project.curated.md
  -> p2p project publish validate
  -> outputs/latest/publication-validation.yml
  -> p2p project publish render
  -> outputs/latest/project.pdf draft
  -> p2p project publish review
  -> outputs/latest/publication-review.yml
```

The feature builds on the existing visible project export. It does not replace
`outputs/latest/project.md`; it adds a curated publication layer above it.

## Canonical Output Principle

The pipeline SHALL produce one canonical human publication of the project:

```text
outputs/latest/project.curated.md
outputs/latest/project.pdf
```

The output represents "project X in vertical Y is this". The feature SHALL NOT
produce commercial, technical, investor, executive, or audience-specific variants
in this pipeline. Downstream users may derive their own variants with other
tools, but those variants are outside this feature.

## In Scope

- A fixed first-slice publication profile manifest.
- A bounded input contract for the curator.
- A formal import step for curator output.
- A `p2p-project-curator` skill or equivalent local agent instruction package.
- A curated Markdown output at `outputs/latest/project.curated.md`.
- A deterministic publication validator for curated Markdown.
- A neutral WeasyPrint-backed PDF rendering step that consumes only validated
  curated Markdown when the optional PDF capability is installed.
- A manual owner review result for the Markdown plus rendered draft PDF package.
- Hash-based provenance and staleness tracking for derived publication stages.
- CLI orchestration for prepare, import, validate, render, review, and status.
- MCP parity decisions for every public workflow added.
- Tests for service, CLI, validation, provenance, import, invalidation, and
  renderer boundary behavior.

## Out Of Scope

- Replacing `.p2p/` as source of truth.
- Mutating `.p2p/` from the curator, validator, renderer, or publication review.
- Treating the curated document or PDF as governance evidence.
- Running an external model call from the deterministic CLI by default.
- Creating a fully automated owner approval decision.
- Producing audience-specific or purpose-specific publication variants.
- Making `audience`, `depth`, or `theme` user-configurable in the first slice.
- Designing branded publication themes beyond `neutral-v1`.
- Maintaining a handcrafted low-quality PDF fallback.
- Producing a rich appendix package in the first slice unless needed to keep the
  single canonical document readable.

## Functional Requirements

- R001: WHEN the publication pipeline is prepared, THE SYSTEM SHALL use
  `outputs/latest/project.md` as the complete input export and SHALL NOT
  overwrite it with curated content.
- R002: THE SYSTEM SHALL write canonical curated human-facing Markdown to
  `outputs/latest/project.curated.md` only through an explicit publication import
  step.
- R003: THE SYSTEM SHALL preserve `.p2p/` as the managed source of truth and
  SHALL NOT read `project.curated.md`, `project.pdf`, or publication metadata as
  governance state.
- R004: THE SYSTEM SHALL keep complete export, curator input, curated Markdown,
  validation result, rendered PDF, owner review result, and manifest/provenance
  data as separate inspectable stages.
- R005: THE SYSTEM SHALL generate a first-slice publication profile manifest
  with resolved values: audience `mixed`, depth `standard`, language
  `project_default`, vertical structure `adaptive`, appendix inclusion `false`,
  and theme `neutral-v1`.
- R006: THE SYSTEM SHALL treat the publication profile as a fixed applied
  manifest in the first slice, not as a configurable variant-selection API.
- R007: WHEN `p2p project publish prepare` runs, THE SYSTEM SHALL compute the
  current P2P source fingerprint, verify or generate
  `outputs/latest/project.md`, compute the export `sha256`, write
  `publication-profile.yml`, write `curator-input.md`, write/update
  `publication-manifest.yml`, and SHALL NOT create `project.curated.md`.
- R008: THE current P2P source fingerprint SHALL be deterministic and SHALL
  cover the source inputs used by the visible project export, including project
  state, proposal registry, decision registry, active vertical/definition state,
  and any existing visible-export source manifest when available.
- R009: THE SYSTEM SHALL treat `outputs/latest/project.md` as stale only when it
  is missing, its recorded P2P source fingerprint differs from the current P2P
  source fingerprint, or its recorded export hash does not match the current
  file contents.
- R010: IF `prepare` finds the recorded P2P source fingerprint unchanged and
  `outputs/latest/project.md` hash-valid, THEN THE SYSTEM SHALL reuse
  `project.md`, SHALL NOT run visible export, and SHALL NOT create a new
  `outputs/review-###/` archive snapshot.
- R011: IF `prepare` finds the P2P source fingerprint changed, missing, or
  invalid, THEN THE SYSTEM SHALL run the visible project export, preserve the
  existing visible-export archive behavior, record the new source fingerprint,
  and invalidate downstream publication stages.
- R012: THE curator input packet SHALL include the source export path and hash,
  P2P source fingerprint, publication profile hash, active vertical summary if
  available, source-of-truth boundary, state distinction guidance, and
  traceability inputs.
- R013: THE SYSTEM SHALL provide curator instructions that prioritize a coherent
  project-first narrative over mirroring proposal file structure.
- R014: THE CURATOR SHALL identify the central project thesis from current P2P
  project state, accepted decisions, active vertical, and project definition
  evidence.
- R015: THE CURATOR SHALL adapt headings, grouping, terminology, and explanatory
  order to the active project vertical when vertical evidence is available.
- R016: THE CURATOR SHALL produce one canonical project document and SHALL NOT
  split the output into audience-specific versions.
- R017: THE CURATOR SHALL distinguish current state, implemented capabilities,
  accepted/planned work, pending decisions, missing evidence, legacy context,
  risks, assumptions, and open questions.
- R018: THE CURATOR SHALL group proposal-derived evidence by project capability
  or product concern instead of dumping proposals chronologically in the main
  body.
- R019: THE CURATOR SHALL remove known placeholders, repeated boilerplate, empty
  sections, and internal governance noise from the main publication body.
- R020: THE CURATOR SHALL preserve source traceability for material claims using
  proposal IDs, decision IDs, Change Set IDs, Work IDs, or source artifact paths.
- R021: THE CURATOR SHALL preserve unresolved risks, assumptions, and open
  questions when they materially affect understanding of the project.
- R022: WHEN `p2p project publish import <file>` runs, THE SYSTEM SHALL verify
  that a current curator input packet exists, reject unsafe paths, copy the file
  atomically to `outputs/latest/project.curated.md`, compute its `sha256`, and
  record the source export hash, P2P source fingerprint, and profile hash used
  for the import.
- R023: THE SYSTEM SHALL validate curated Markdown before rendering PDF.
- R024: THE VALIDATOR SHALL emit findings with severity `error`, `warning`, or
  `advisory`.
- R025: THE VALIDATOR SHALL fail deterministic contract errors, including
  missing curated file, invalid profile/manifest, missing source fingerprint,
  missing source export hash, incorrect H1 count, missing executive summary,
  missing source-of-truth statement, unsafe output path, or Markdown that cannot
  be processed by the renderer.
- R026: THE VALIDATOR SHALL warn or advise on heuristic concerns, including
  possible proposal dumps, weak traceability density, excessive `PROP-` heading
  repetition, overly long chapters, weak state distinctions, or missing apparent
  vertical framing.
- R027: THE SYSTEM SHALL use recorded hashes and P2P source fingerprints, not
  filesystem modification times, as the primary staleness and provenance
  mechanism.
- R028: IF the current P2P source fingerprint differs from the fingerprint used
  for the current `project.md`, or if `project.md` hash changes, THEN curator
  input, curated Markdown, validation, PDF, and review SHALL be reported stale
  until regenerated or re-imported.
- R029: IF `project.curated.md` hash changes, THEN validation, PDF, and review
  SHALL be reported stale until regenerated.
- R030: IF profile/theme hash changes, THEN validation, PDF, and review SHALL be
  reported stale until regenerated.
- R031: THE PDF RENDERER SHALL consume only validated `project.curated.md` and
  SHALL NOT perform semantic editing.
- R032: THE PDF RENDERER SHALL write neutral draft PDF output to
  `outputs/latest/project.pdf`.
- R033: THE SYSTEM SHALL keep PDF rendering out of the base runtime dependency
  set and SHALL provide PDF rendering through an explicit optional capability
  intended to be installed as `p2p-engine[pdf]`.
- R034: THE optional PDF capability SHALL use a Markdown-to-HTML-to-`neutral-v1`
  CSS-to-WeasyPrint adapter unless implementation validation discovers a
  concrete blocker that is recorded before coding continues.
- R035: THE SYSTEM SHALL NOT implement a handcrafted low-quality PDF fallback.
- R036: THE owner review stage SHALL review the publication package, including
  `project.curated.md` and `project.pdf`, and SHALL record `approved` or
  `changes_requested`.
- R037: THE SYSTEM SHALL NOT treat a PDF as approved for publication until owner
  review records `approved` for the current curated Markdown hash and PDF hash.
- R038: WHEN publication status is requested, THE SYSTEM SHALL report the paths,
  hashes, P2P source fingerprint, readiness, staleness, validation status,
  render status, review status, and `approved_for_publication` state for every
  publication stage.
- R039: IF CLI commands are added for publication, THEN THE SYSTEM SHALL expose
  project-level commands rather than Change Set or software-spec commands.
- R040: IF MCP exposes publication commands, THEN write operations SHALL be
  write-safe derived-output operations and SHALL NOT mutate governance state.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep deterministic stages runnable without network
  access.
- N002: THE SYSTEM SHALL make agentic curation an explicit external/human-agent
  step unless a future accepted proposal introduces model execution inside P2P
  Engine.
- N003: THE SYSTEM SHALL keep publication outputs under the repository
  `outputs/` tree.
- N004: THE SYSTEM SHALL record source paths, P2P source fingerprint, sha256
  hashes, profile identity, generator identity, validation status, render
  status, review status, and timestamps in `publication-manifest.yml` and
  related reports.
- N005: THE SYSTEM SHALL preserve the base runtime without PDF-specific
  dependencies; PDF rendering belongs to an optional install/runtime capability.
- N006: THE SYSTEM SHALL implement runtime behavior behind cohesive services,
  validators, renderers, and CLI/MCP adapters rather than adding large behavior
  directly to `P2PWorkspace`, `cli.py`, or MCP tool dispatchers.
- N007: THE SYSTEM SHALL preserve existing `p2p project export`,
  `p2p_project_export`, and spec-export behavior.

## Edge Cases And Errors

- E001: IF `outputs/latest/project.md` is missing or stale by P2P source
  fingerprint or export hash, THEN prepare SHALL run the visible project export
  automatically, report that action, preserve the existing export archive
  behavior, and record the new source fingerprint and export hash.
- E002: IF `project.curated.md` is missing, THEN validation SHALL fail with a
  clear missing-curated-output error.
- E003: IF the curated output was imported against a source fingerprint or source
  export hash different from the current prepared values, THEN status SHALL mark
  curation as stale.
- E004: IF validation fails with any `error`, THEN rendering SHALL refuse to
  write or refresh `project.pdf`.
- E005: IF owner review is missing, THEN status SHALL report the PDF as rendered
  but not approved for publication.
- E006: IF no active vertical is configured, THEN the curator SHALL use a
  generic project-first structure and mark vertical evidence as unavailable.
- E007: IF PDF rendering dependencies are unavailable, THEN the renderer SHALL
  fail with a clear `p2p-engine[pdf]` optional-install/configuration message and
  SHALL NOT alter curated Markdown.
- E008: IF output paths would escape the repository `outputs/` directory, THEN
  the operation SHALL fail.
- E009: IF an import source path attempts traversal outside allowed input roots,
  THEN import SHALL fail before reading or copying the file.
- E010: IF a previous review references stale curated Markdown or PDF hashes,
  THEN status SHALL report `review_stale`.

## Acceptance Criteria

- AC001: A local `p2p-project-curator` skill or instruction package exists and
  describes the curator role, input contract, output contract, vertical-aware
  editorial rules, traceability rules, canonical single-output rule, and
  non-governance boundary.
- AC002: `p2p project publish prepare` creates or identifies
  `outputs/latest/project.md`, writes `publication-profile.yml`, writes
  `curator-input.md`, records source fingerprint and source/profile hashes, and
  does not create a new `outputs/review-###/` snapshot when the source
  fingerprint is unchanged.
- AC003: `p2p project publish import <file>` atomically writes
  `outputs/latest/project.curated.md` and records source/profile/curated hashes
  plus source fingerprint without overwriting `outputs/latest/project.md`.
- AC004: Publication validation reports pass/fail status and
  error/warning/advisory findings for the curated document contract.
- AC005: Rendering refuses invalid curated Markdown and renders valid curated
  Markdown to `outputs/latest/project.pdf` through the WeasyPrint-backed
  optional PDF capability when it is available.
- AC006: Owner review records whether the current Markdown/PDF package is
  approved or needs changes without implying P2P governance acceptance.
- AC007: Publication status reports complete export, curator input, curated
  Markdown, validation, PDF, review, staleness, and
  `approved_for_publication` separately.
- AC008: Tests cover service-level status, hash provenance, cascading
  invalidation, import safety, validation findings, CLI behavior if added, MCP
  behavior if added, and PDF renderer boundary behavior.
- AC009: Existing visible project export and spec-export tests continue to pass.
- AC010: Documentation explains the difference between complete export, canonical
  curated publication, validation, draft PDF rendering, owner review, and
  publication approval.
