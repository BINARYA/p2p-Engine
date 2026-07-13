# Tasks - PROP-099 Human Project Publication Pipeline

## Preparation

- [x] T001: Confirm owner governance decision for `PROP-099`; completion is
  `p2p proposal show PROP-099` reporting `status: accepted`.
- [x] T002: Review existing visible export behavior; completion is confirmation
  of the current `p2p project export` output shape, archive behavior, and any
  existing source fingerprint/manifest that can be reused.
- [x] T003: Choose the concrete optional PDF adapter; completion is this spec
  naming Markdown-to-HTML-to-`neutral-v1`-CSS-to-WeasyPrint through
  `p2p-engine[pdf]`, with no handcrafted fallback.
- [x] T004: Resolve curator skill location; completion is this spec naming
  the P2P Engine release template layer as the canonical source, with
  `.agents/`, `.codex/`, `CLAUDE.md`, or other adapter locations treated as
  generated outputs.
- [x] T005: Decide prepare behavior; completion is this spec requiring
  `p2p project publish prepare` to auto-run the visible project export when
  `outputs/latest/project.md` is missing or stale by source fingerprint or
  export hash, and to remain idempotent when unchanged.

## Implementation Slices

- [x] S001: Slice A - implement publication model, manifest, hash provenance,
  prepare, curator packet, import, and status; completion is a usable pipeline
  through imported `project.curated.md` without validation/render/review.
- [x] S002: Slice B - implement validation and cascading invalidation; completion
  is deterministic validation reports and freshness checks across source,
  profile, packet, curated, validation, PDF, and review stages.
- [x] S003: Slice C - implement WeasyPrint PDF rendering, owner review, CLI/MCP
  parity, docs, and end-to-end regression coverage.

## Curator Skill And Contracts

- [x] T006: Create the `p2p-project-curator` skill/instruction package;
  completion is a skill that defines role, inputs, canonical single-output rule,
  vertical-aware editing, traceability, source-of-truth boundary, and forbidden
  behaviors, generated from release templates with ownership, hash/drift
  detection, update policy, uninstall safety, and Codex/Claude adapter behavior.
- [x] T007: Define the curator packet schema; completion is documented fields for
  source path/hash, P2P source fingerprint, profile path/hash, vertical summary,
  state distinctions, traceability inputs, and canonical-output instructions.
- [x] T008: Implement curator packet builder; completion is deterministic
  generation of `outputs/latest/curator-input.md`.
- [x] T009: Add curator packet tests; completion covers missing vertical,
  present vertical, P2P source fingerprint, source export hash, profile hash,
  and source-of-truth text.
- [x] T010: Implement publication profile manifest generation; completion is
  `outputs/latest/publication-profile.yml` with fixed resolved values, not a
  configurable variant API.
- [x] T011: Implement curator import; completion is
  `p2p project publish import <file>` atomically writing
  `outputs/latest/project.curated.md` and recording source/profile/curated
  hashes plus the P2P source fingerprint.
- [x] T012: Add curator import safety tests; completion covers missing packet,
  stale packet, unsafe path, source fingerprint mismatch, source export hash
  mismatch, and successful import.

## Publication Model And Services

- [x] T013: Add publication path/model types; completion is a small model for
  stage paths, hashes, freshness, and status without service orchestration.
- [x] T014: Add manifest read/write helpers; completion is
  `publication-manifest.yml` persisted with source fingerprint, source export,
  profile, packet, curated, validation, render, and review stage hashes.
- [x] T015: Add hash utility coverage; completion is deterministic sha256
  calculation for text/binary stage artifacts and deterministic source
  fingerprint construction or reuse.
- [x] T016: Add publication status service; completion is stage-level status for
  complete export, curator input, curated Markdown, validation, PDF, review, and
  `approved_for_publication`.
- [x] T017: Add cascading invalidation rules; completion is hash-based stale
  detection for source fingerprint, source export hash, profile, curated,
  validation, PDF, and review changes.
- [x] T018: Add publication orchestration service; completion is prepare,
  import, validate, render, review, and status orchestration without mutating
  `.p2p/`, including idempotent prepare behavior that avoids duplicate
  `outputs/review-###/` snapshots when the source is unchanged.

## Validation

- [x] T019: Define validation finding codes and severity policy; completion is a
  documented catalog separating `error`, `warning`, and `advisory`.
- [x] T020: Define placeholder and proposal-dump heuristics; completion is a
  small deterministic catalog with tests for known placeholder phrases and
  repeated proposal-template patterns.
- [x] T021: Implement deterministic validation errors; completion covers missing
  curated file, invalid manifest/profile, missing hashes, wrong H1 count,
  missing executive summary, missing source-of-truth statement, unsafe paths,
  and renderer-incompatible Markdown.
- [x] T022: Implement heuristic validation warnings/advisories; completion covers
  possible proposal dump, weak traceability density, repeated `PROP-` headings,
  overly long chapters, weak state distinctions, and missing apparent vertical
  framing.
- [x] T023: Add validation report writing; completion is
  `outputs/latest/publication-validation.yml` with status, input hashes, and
  findings.
- [x] T024: Add validator tests; completion covers pass, deterministic failure,
  warnings-only pass, advisory findings, and hash mismatch behavior.

## Rendering And Review

- [x] T025: Implement optional PDF capability detection; completion is render
  commands failing clearly with `p2p-engine[pdf]` guidance when the optional
  capability or native dependencies are unavailable.
- [x] T026: Implement neutral PDF renderer adapter after T003/T025; completion is
  Markdown-to-HTML-to-`neutral-v1`-CSS-to-WeasyPrint producing
  `outputs/latest/project.pdf` from validated curated Markdown.
- [x] T027: Add renderer tests; completion covers refusal on failed validation,
  refusal on stale validation, unavailable PDF capability, Unicode Italian text,
  tables, code blocks, multi-page input, and successful PDF output.
- [x] T028: Implement owner review metadata handling after render; completion is
  explicit writing of `outputs/latest/publication-review.yml` for
  `approved` or `changes_requested` against current curated/PDF hashes.
- [x] T029: Add review tests; completion covers missing PDF, stale PDF, stale
  curated hash, approved package, changes requested, and review invalidation
  after re-render.

## CLI And MCP

- [x] T030: Add project-level publish CLI command group; completion is
  `p2p project publish prepare`, `import`, `validate`, `render`, `review`, and
  `status`.
- [x] T031: Keep CLI command bodies thin; completion is delegation to services
  rather than publication logic inside `project_ops.py`.
- [x] T032: Add CLI tests for each publish command; completion is observable
  output and generated files under a temporary repository.
- [x] T033: Add MCP read-only publication status; completion is schema, handler,
  and tests for stage state payloads.
- [x] T034: Add MCP write-safe prepare/import/validate/render if public CLI
  commands are implemented; completion is schema, handler, and tests proving no
  `.p2p` mutation and strict import path validation.
- [x] T035: Document no first-slice MCP review/curate tools; completion is docs
  and catalog absence for owner review and model execution.

## End-To-End And Regression Tests

- [x] T036: Add end-to-end boundary test without LLM; completion covers
  `prepare -> simulated curator output -> import -> validate -> render -> status`.
- [x] T037: Add owner review loop test; completion covers
  `prepare -> import -> validate -> render -> changes_requested -> re-import ->
  validate -> render -> approved`.
- [x] T038: Add cascading invalidation test; completion covers source export
  fingerprint change, source export hash change, unchanged-source idempotence,
  curated hash change, validation hash change, theme/profile change, stale PDF,
  and stale review.
- [x] T039: Add import provenance test; completion rejects curated output derived
  from the wrong packet, stale source fingerprint, or stale source export hash.
- [x] T040: Add path traversal tests for prepare/import/render output paths;
  completion covers fixed prepare/render outputs under `outputs/latest/`, import
  rejection for sources outside the project root, import rejection for sources
  under `.p2p/`, and import rejection for the canonical output path.
- [x] T041: Run focused validation:
  `.venv/bin/pytest tests/test_visible_project_export.py tests/test_cli.py -k "project or publish or publication"`;
  completion is passing output or a narrower documented focused command if test
  locations differ after implementation.
- [x] T042: Run public-contract validation if CLI/MCP commands are added:
  `./scripts/test-public.sh`; completion is passing output.
- [x] T043: Run full validation before handoff:
  `./scripts/test-full.sh`; completion is passing output or an explicit residual
  risk if deferred by owner.
- [x] T044: Run `p2p validate`; completion is no validation errors from P2P
  project state.

## Documentation And Handoff

- [x] T045: Update `docs/CLI-GUIDE.md`; completion explains complete export,
  canonical curated publication, prepare/import, validation, draft PDF rendering,
  owner review, approval state, and status.
- [x] T046: Update `docs/MCP.md` if MCP tools are added; completion documents
  tool safety level, import constraints, derived-output boundary, and lack of
  review/curate MCP tools in the first slice.
- [x] T047: Add implementation note after delivery; completion records files
  changed, commands added, test evidence, renderer dependency decision, MCP
  parity decision, and known follow-ups.

## Follow-Up Candidates

- [ ] F001: Add appendix package support with `project.appendix.md` while keeping
  one canonical main publication.
- [ ] F002: Add richer neutral rendering polish after `neutral-v1` proves stable.
- [ ] F003: Add publication package manifest export for downstream tools.
- [ ] F004: Revisit whether `outputs/latest/project.md` should later be renamed
  to `project.full.md` with a compatibility migration.
