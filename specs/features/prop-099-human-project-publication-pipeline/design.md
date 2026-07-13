# Design - PROP-099 Human Project Publication Pipeline

## Requirements Covered

- R001-R040, N001-N007, E001-E010

## Key Decisions

- D001: Treat publication as a staged pipeline above the existing visible export.
  Rationale: `outputs/latest/project.md` is complete and traceable; the new
  feature must improve readability without losing the complete export or
  confusing source-of-truth boundaries.

- D002: Produce exactly one canonical human publication.
  Rationale: P2P should publish "the project" as a coherent vertical-aware
  document. Commercial, technical, investor, executive, or other adaptations are
  downstream uses, not outputs of this pipeline.

- D003: Keep agentic curation outside deterministic runtime execution in the
  first slice.
  Rationale: the agentic step is the primary quality driver, but embedding model
  execution into the CLI would introduce provider, credential, latency, and
  reproducibility concerns that are not needed for the initial pipeline.

- D004: Make curator import a formal pipeline stage.
  Rationale: the highest-value transformation is external and semantic, so the
  deterministic system must bind that output to a known source export, profile,
  and hash instead of relying on direct informal writes to `outputs/latest/`.

- D005: Use hash provenance for staleness and invalidation.
  Rationale: filesystem timestamps are fragile across Git checkout, copy,
  archive, and regeneration operations. Stage validity must be tied to recorded
  content hashes.

- D006: Validate before rendering.
  Rationale: the PDF renderer should be presentation-only; it must not hide
  missing structure, poor traceability, or proposal dumps behind a polished file.

- D007: Render a draft PDF before owner review.
  Rationale: the owner should review both semantic content and rendered output,
  including pagination, tables, code blocks, links, and readability.

- D008: Keep owner review separate from validation.
  Rationale: deterministic validation checks document contract compliance, while
  the owner verifies meaning, emphasis, vertical fit, rendered quality, and
  publishability.

- D009: Use a fixed first-slice profile manifest.
  Rationale: `mixed`, `standard`, and `neutral-v1` describe the canonical
  publication contract. They are not user-selectable variants in this feature.

- D010: Keep PDF rendering optional and avoid a handcrafted fallback.
  Rationale: base P2P should remain lightweight. A low-quality custom PDF
  renderer would create maintenance cost without producing a useful publication
  artifact.

- D011: Use WeasyPrint behind an optional `p2p-engine[pdf]` capability.
  Rationale: WeasyPrint gives a controlled Markdown-to-HTML-to-CSS-to-PDF path,
  avoids a LaTeX dependency, avoids shelling out to Pandoc as the primary path,
  and can be isolated behind a renderer adapter. The command must still report
  native dependency or install problems clearly.

- D012: Store the curator skill source in the P2P Engine release template layer.
  Rationale: the curator is a reusable P2P Engine capability. Project-local
  agent files under `.agents/`, `.codex/`, `CLAUDE.md`, or other adapter
  locations are generated outputs managed by the agent integration lifecycle;
  they are not release-template source.

- D013: Make `prepare` the pipeline entry point.
  Rationale: users should not need to remember a separate export command before
  publication. `prepare` may run the existing visible export when needed, while
  still reporting that action and preserving existing archive behavior.

- D014: Close MCP parity semantics in the design.
  Rationale: publication commands touch derived outputs and agent-facing
  workflow, so parity must be explicit before implementation.

## Existing Foundation

The repository already has:

- `p2p project export`, which writes `outputs/latest/project.md`;
- `p2p project export-status`, which reports visible export status;
- MCP tools `p2p_project_export` and `p2p_project_export_status`;
- `VisibleProjectExportService`, which owns the complete visible export;
- vertical/runtime state surfaced in visible exports.

This feature should reuse that foundation and add publication-stage behavior
next to it.

## Proposed Components

- `src/p2p_engine/services/project_publication.py`
  Owns publication paths, stage model, manifest read/write, hash calculation,
  status, prepare, import, validation orchestration, render orchestration, owner
  review metadata, and cascading invalidation.

- `src/p2p_engine/services/project_publication_validation.py`
  Deterministic curated Markdown validator. It returns structured findings with
  severity, code, message, and source line when practical.

- `src/p2p_engine/services/project_publication_rendering.py`
  Neutral renderer adapter. The preferred strategy is Markdown to HTML to
  `neutral-v1` CSS to PDF through WeasyPrint, exposed through an optional
  `p2p-engine[pdf]` extra. If the optional capability or native dependencies
  are missing, render fails clearly and does not modify curated Markdown.

- `src/p2p_engine/cli_commands/project_ops.py`
  Project-level CLI wiring. Keep command bodies thin and delegate to services.

- `src/p2p_engine/mcp/catalog/project.py` and
  `src/p2p_engine/mcp/handlers/project.py`
  MCP parity for status, prepare, import, validate, and render.
  Owner review is intentionally not exposed over MCP in the first slice.

- `src/p2p_engine/services/agent_templates.py`
  Release template source for the curator instructions and adapter-specific
  generated outputs. This is the canonical source for curator instructions in
  the P2P Engine release; project-local adapter files are generated from it.

- `.agents/skills/p2p-project-curator/SKILL.md`
  Generated Codex-compatible project skill output for producing one canonical
  project document from the bounded input packet.

- `.codex/skills/p2p-project-curator/SKILL.md`
  Generated legacy Codex skill output for direct Codex discovery when needed.

- `CLAUDE.md`
  Generated Claude adapter instructions include equivalent publication curator
  guidance in the structure currently supported by P2P Engine.

- `docs/CLI-GUIDE.md`, `docs/MCP.md`
  User-facing command and boundary documentation.

## Output Shape

First slice:

```text
outputs/
  latest/
    project.md
    curator-input.md
    project.curated.md
    project.pdf
    publication-profile.yml
    publication-manifest.yml
    publication-validation.yml
    publication-review.yml
```

`project.md` remains the complete visible export. `project.curated.md` and
`project.pdf` are the canonical human publication outputs.

Optional later slice:

```text
outputs/
  latest/
    project.appendix.md
    render-report.yml
```

The first slice should not rename the existing `project.md`. If a later slice
introduces `project.full.md`, it needs a compatibility plan and should not create
multiple audience-specific publication outputs.

## Publication Profile Manifest

Initial resolved manifest values:

```yaml
schema_version: 1
profile_id: neutral-v1-standard
profile_role: fixed_applied_manifest
resolved_values:
  audience: mixed
  depth: standard
  language: project_default
  vertical_structure: adaptive
  include_appendix: false
  theme: neutral-v1
```

This file records what was applied. It is not a user-facing configuration API in
the first slice.

## Publication Manifest

`publication-manifest.yml` records stage provenance:

```yaml
schema_version: 1
pipeline: human_project_publication
publication_role: canonical_human_publication
governance_authority: derived
source_of_truth: .p2p/
source_state:
  fingerprint_sha256: ...
  inputs:
    project_state_sha256: ...
    proposals_registry_sha256: ...
    decisions_registry_sha256: ...
    vertical_definition_sha256: ...
    visible_export_source_manifest_sha256: ...
stages:
  source_export:
    path: outputs/latest/project.md
    source_fingerprint_sha256: ...
    sha256: ...
  profile:
    path: outputs/latest/publication-profile.yml
    sha256: ...
  curator_packet:
    path: outputs/latest/curator-input.md
    source_fingerprint_sha256: ...
    source_sha256: ...
    profile_sha256: ...
    sha256: ...
  curated:
    path: outputs/latest/project.curated.md
    source_fingerprint_sha256: ...
    source_sha256: ...
    profile_sha256: ...
    sha256: ...
  validation:
    path: outputs/latest/publication-validation.yml
    curated_sha256: ...
    validator_version: ...
    status: passed
  render:
    path: outputs/latest/project.pdf
    curated_sha256: ...
    validation_sha256: ...
    theme: neutral-v1
    sha256: ...
  review:
    path: outputs/latest/publication-review.yml
    curated_sha256: ...
    pdf_sha256: ...
    status: approved
```

Status should derive freshness from these hashes, not from file modification
times.

## P2P Source Fingerprint

`project.md` staleness is based on a deterministic fingerprint of the P2P source
state used by the visible project export, not on filesystem timestamps.

The fingerprint should reuse an existing visible-export source fingerprint if
that service exposes one. If it does not, the first implementation should build
one from stable source inputs such as:

- project state;
- proposal registry;
- decision registry;
- active vertical and definition state;
- visible-export source manifest when available.

The stale rule is:

```text
current P2P source fingerprint != fingerprint recorded for latest project.md
```

`project.md` is also stale when its recorded export hash does not match the
current file contents.

## Prepare Contract

`p2p project publish prepare`:

1. computes the current P2P source fingerprint;
2. compares it to the fingerprint recorded for `outputs/latest/project.md`;
3. reuses `project.md` when the fingerprint and export hash are unchanged;
4. runs the existing visible project export when `project.md` is missing, stale,
   or hash-invalid;
5. computes the source export hash;
6. writes `publication-profile.yml` as a fixed applied manifest;
7. writes `curator-input.md`;
8. writes or updates `publication-manifest.yml`;
9. reports stale downstream stages if source/profile hashes changed;
10. does not run the curator;
11. does not create or modify `project.curated.md`.

If `project.md` is missing or stale, prepare runs the existing visible project
export before writing publication artifacts. It must report that it ran the
export, preserve existing `p2p project export` archive behavior, record the new
source fingerprint and export hash, and invalidate downstream publication
stages.

If the current P2P source fingerprint is unchanged and the recorded
`project.md` hash still matches the file, prepare must be idempotent: it reuses
`project.md`, does not run visible export, and does not create a new
`outputs/review-###/` snapshot. It may regenerate missing publication profile,
manifest, or curator packet artifacts when their expected hashes are absent or
invalid.

## Curator Input Contract

The curator receives `curator-input.md` rather than the whole repository:

- required: `outputs/latest/project.md`;
- required: source export sha256;
- required: P2P source fingerprint;
- required: publication profile path and sha256;
- required: active vertical summary if available;
- required: source-of-truth boundary statement;
- required: canonical single-output instruction;
- required: state distinction guidance;
- optional: proposal/decision index for traceability;
- optional: accepted/planned/pending/missing state summary;
- optional: owner-provided publication emphasis.

The curator may request more source context, but the initial packet should push
toward compact, publication-oriented editing.

## Curator Import Contract

`p2p project publish import <file>`:

1. verifies that `curator-input.md` and `publication-manifest.yml` exist;
2. verifies that the source fingerprint, source export hash, and profile hashes
   still match current files and manifest values;
3. rejects unsafe paths and path traversal;
4. reads the provided file;
5. writes `project.curated.md` atomically;
6. records imported file hash, source fingerprint, source export hash, profile
   hash, and import metadata;
7. marks validation, render, and review stale.

The external agent should not write directly to the canonical
`outputs/latest/project.curated.md` path as the normal pipeline path.

## Curator Output Contract

`project.curated.md` must:

- contain exactly one H1;
- include an executive summary;
- explain the project first, then supporting governance history;
- use a structure compatible with the active vertical;
- represent one canonical project output, not audience-specific variants;
- distinguish current, planned, pending, missing, partial, implemented, and
  legacy information;
- keep traceability for material claims;
- preserve material risks, assumptions, and open questions;
- avoid placeholders, empty sections, repeated boilerplate, and wholesale
  proposal dumps in the main body;
- include a source-of-truth warning that `.p2p/` remains authoritative.

## Validation Contract

Validation emits `publication-validation.yml`:

```yaml
schema_version: 1
status: passed | failed
validated_at: YYYY-MM-DD
input: outputs/latest/project.curated.md
curated_sha256: ...
profile: outputs/latest/publication-profile.yml
profile_sha256: ...
findings:
  - severity: error | warning | advisory
    code: single_h1_missing
    message: Curated document must contain exactly one H1.
    line: 1
```

Deterministic errors:

- missing curated file;
- invalid profile or manifest;
- missing source/profile/curated hash;
- wrong H1 count;
- missing executive summary;
- missing source-of-truth statement;
- unsafe output path;
- Markdown cannot be processed by the renderer.

Heuristic warnings/advisories:

- probable proposal dump;
- chapters too long;
- weak traceability density;
- repeated `PROP-` headings in the main body;
- weak current/planned/pending/missing distinction;
- vertical/domain section apparently missing.

Owner review, not validation, judges narrative quality, tone, emphasis, and
audience suitability of the canonical document.

## PDF Rendering Contract

Rendering:

1. reads `publication-validation.yml`;
2. requires validation `status: passed`;
3. reads `project.curated.md`;
4. applies `neutral-v1`;
5. writes draft `project.pdf`;
6. records PDF hash and render metadata in the manifest or render report.

Rendering must not rewrite `project.curated.md`. Rendering is unavailable when
the optional PDF capability is not installed, and the command must explain the
`p2p-engine[pdf]` install/configuration requirement. The primary renderer path
is:

```text
Markdown -> HTML -> neutral-v1 CSS -> WeasyPrint -> PDF
```

## Owner Review Contract

Owner review happens after draft PDF rendering and emits
`publication-review.yml` only through an explicit owner action:

```yaml
schema_version: 1
status: approved | changes_requested
reviewed_at: YYYY-MM-DD
reviewer: owner
reviewed_artifacts:
  - path: outputs/latest/project.curated.md
    sha256: ...
  - path: outputs/latest/project.pdf
    sha256: ...
validation: outputs/latest/publication-validation.yml
notes:
  - Review note.
```

Status should distinguish:

```text
rendered
reviewed
approved_for_publication
```

This file is publication review metadata. It must not be interpreted as proposal
acceptance, Work acceptance, or governance approval.

## CLI Shape

First-slice CLI:

```bash
p2p project publish prepare
p2p project publish import <file>
p2p project publish validate
p2p project publish render
p2p project publish review --status approved --reviewer owner --note "..."
p2p project publish status
```

The nested `project publish ...` shape keeps the feature as a coherent pipeline
and avoids adding many flat project commands.

## MCP Parity

If CLI commands are implemented:

- `status`: yes, read-only MCP parity.
- `prepare`: yes, write-safe derived-output parity.
- `import`: yes, write-safe parity only with strict path validation and no
  `.p2p` mutation.
- `validate`: yes, write-safe parity because it writes a derived validation
  report only.
- `render`: yes, write-safe parity if the optional PDF capability is available
  and validation has passed.
- `review`: no MCP parity in the first slice.
- `curate`: no deterministic MCP behavior in the first slice.

## Cascading Invalidation

Status uses this dependency graph:

```text
project.md
  -> curator-input.md
  -> project.curated.md
  -> publication-validation.yml
  -> project.pdf
  -> publication-review.yml
```

Rules:

- if the current P2P source fingerprint differs from the fingerprint recorded
  for `project.md`, every downstream stage is stale;
- if `project.md` hash changes, every downstream stage is stale;
- if `publication-profile.yml` hash changes, curator input, curated output,
  validation, PDF, and review are stale;
- if `project.curated.md` hash changes, validation, PDF, and review are stale;
- if validation hash changes, PDF and review are stale;
- if `project.pdf` hash changes, review is stale;
- changing only `publication-review.yml` does not invalidate content.

## Compatibility

- Existing `outputs/latest/project.md` remains the complete visible export.
- Existing review snapshot behavior for `p2p project export` remains unchanged.
- Existing `.p2p/outputs/spec-export/...` behavior remains unchanged.
- Existing MCP project export tools remain valid.
- Publication outputs must be safe to delete and regenerate because they are
  derived outputs.

## Risks And Tradeoffs

- RISK: A deterministic validator can pass a document that is still editorially
  weak.
  Mitigation: keep owner review and agentic curation explicit.

- RISK: A polished PDF can be mistaken for governance truth.
  Mitigation: source-of-truth warning, traceability, and docs.

- RISK: PDF dependencies can make installation fragile.
  Mitigation: keep PDF support optional and fail render commands clearly when the
  optional capability is unavailable.

- RISK: Curator variability can make output inconsistent.
  Mitigation: fixed profile manifest, input packet, import contract, output
  contract, validation, and review.

## Resolved Implementation Decisions

- RID001: The first slice produces one canonical publication output only.
- RID002: Curator output enters the canonical pipeline through explicit import.
- RID003: Staleness is hash-based, not timestamp-based.
- RID004: Review follows draft PDF rendering and approves or rejects the current
  Markdown/PDF package.
- RID005: PDF rendering is optional-capability based; no handcrafted fallback.
- RID006: The first-slice CLI command set is `prepare`, `import`, `validate`,
  `render`, `review`, and `status`.
- RID007: The PDF renderer strategy is Markdown to HTML to `neutral-v1` CSS to
  WeasyPrint, exposed through `p2p-engine[pdf]`.
- RID008: The canonical curator instruction source lives in the P2P Engine
  release template layer. Adapter-specific locations such as `.agents/`,
  `.codex/`, and `CLAUDE.md` are generated outputs with hash/drift tracking.
- RID009: `prepare` automatically runs the existing visible project export when
  `outputs/latest/project.md` is missing or stale.
- RID010: `project.md` staleness is based on deterministic P2P source
  fingerprint mismatch or export hash mismatch, not timestamps.
- RID011: `prepare` is idempotent when the source fingerprint and export hash
  are unchanged and must not create duplicate review snapshots in that case.

## Open Implementation Decisions

- None at this spec level. Implementation may still discover adapter-specific
  constraints, but the product and workflow decisions are closed for the first
  slice.
