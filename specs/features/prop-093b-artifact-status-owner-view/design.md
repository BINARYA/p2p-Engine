# PROP-093B Artifact Status And Owner View Design

## Design Summary

`PROP-093B` separates logical proposal completeness from the physical file list.
It builds on the existing proposal artifact state services and adds an explicit
owner full view for decision-time review.

The design should avoid migrations and avoid creating placeholder files. Read
operations derive a stable view from existing proposal state, optional files,
and artifact definitions.

## Key Decisions

### D001: Artifact catalog is a view model

The artifact catalog should be a read model assembled from existing proposal
state and services. It should not require new files to exist.

### D002: Artifact status and readiness remain distinct

Artifact status answers: "Which proposal components exist, are expected, or are
missing?"

Readiness answers: "Is the proposal good enough for an owner decision?"

The full view may include both, but they should remain separate concepts. They
may legitimately disagree; neither view should overwrite, normalize, or hide
the other.

### D003: Full proposal view is explicit and read-only

The full owner view should be available through an additive CLI flag or command
and an MCP read-only surface. Rendering it must not mutate `.p2p/`.

### D004: Provenance is best-effort

For current and future artifacts, provenance can be inferred from known import,
generation, or canonical service paths. For legacy files, provenance may be
reported as `legacy` or `unknown` rather than guessed.

### D005: CLI and MCP share service output

The CLI may render rich text, while MCP returns structured data. Both should
consume the same service-level view model to avoid drift.

### D006: Question sources are separate groups

The full view should not flatten all question-like data into one
`open_questions` bucket. It should distinguish:

- structured owner questions from `questions.yml`;
- analytical open-question contributions from `contributions.yml`;
- legacy or imported narrative question artifacts such as `open-questions.md`.

This preserves compatibility with legacy artifacts while keeping structured
question state authoritative for owner-question readiness.

### D007: Public values are stable and non-duplicative

The view model should expose stable machine-facing values for MCP. Existing
artifact expectation and status enums should be reused where they fit. New
renderer/view fields such as `materialization_kind`, `source_hint`, or
`provenance_confidence` should be introduced only when they express information
that expectation/status cannot express.

Avoid status values such as `missing_required` when the same meaning is already
represented by `expectation=required` and `status=missing`.

### D008: Paths are evidence hints

Paths in CLI and MCP output identify backing evidence or source material. They
are not write targets. Any guidance near paths should point to P2P commands or
explicit write-safe MCP tools.

## Components

### `src/p2p_engine/core/proposal_artifact_state.py`

Owns existing artifact expectation, status, confirmation, and risk enums.

Possible changes:

- add a provenance/materialization enum only if renderer-level labels are not
  sufficient;
- avoid changing persisted state unless required.

### `src/p2p_engine/services/proposal_artifact_state.py`

Owns artifact state definitions and derived state.

Expected changes:

- extend artifact definitions where needed;
- provide deterministic ordering;
- derive status for reduced-footprint and legacy proposals;
- expose enough data for a full proposal view.

### New or existing proposal view service

Preferred approach:

- introduce a cohesive service such as `ProposalFullViewService` or
  `ProposalReviewViewService`;
- or extend an existing proposal service if there is already a clear ownership
  boundary.

Responsibilities:

- collect proposal metadata and core sections;
- collect decision and readiness summary;
- collect structured contributions;
- group owner questions, analytical open-question contributions, and narrative
  question artifacts separately;
- collect optional narrative/imported artifact excerpts or summaries;
- collect logical artifact status;
- apply summary/clipping rules for long narrative artifacts;
- produce a structured view model for CLI/MCP renderers.

### CLI renderer

Likely touched modules:

- `src/p2p_engine/cli_commands/proposal_core.py`;
- proposal rendering helpers if present.

Responsibilities:

- add `--full` or equivalent explicit surface;
- keep default show output stable;
- render sections in a predictable order;
- avoid excessive raw content dumping.
- label paths as evidence/source hints rather than edit targets.

### MCP handler and catalog

Likely touched modules:

- `src/p2p_engine/mcp/catalog/proposals.py`;
- `src/p2p_engine/mcp/handlers/proposals.py`.

Responsibilities:

- expose read-only full view and artifact status data;
- return structured fields, not CLI-formatted text only;
- expose stable public values for artifact status, materialization/provenance,
  question groups, and next actions;
- preserve write boundaries.

## View Model

The service-level full view should include:

- `proposal_id`;
- `title`;
- `status`;
- `core_sections`;
- `decision`;
- `readiness`;
- `contributions`;
- `artifact_status`;
- `questions`;
- `narrative_artifacts`;
- `next_actions`.

`questions` should contain separate groups:

- `owner_questions`;
- `analytical_open_questions`;
- `legacy_question_artifacts`.

Artifact status entries should include:

- `key`;
- `label`;
- `expectation`;
- `status`;
- `materialization_kind`;
- `source_hint`;
- `provenance_confidence`;
- `path`, when a backing file exists;
- `summary`;
- `next_action`.

Suggested public values:

- `materialization_kind`: `canonical_state`, `generated_file`,
  `imported_file`, `legacy_file`, `not_materialized`, `unknown`;
- `provenance_confidence`: `explicit`, `inferred`, `unknown`.

The exact dataclass or dictionary shape can follow existing service patterns.
Expectation/status should reuse existing artifact enums unless a clear gap is
identified during implementation.

## CLI Output Shape

`p2p proposal show PROP-XXX --full` should render in this order:

1. identity and status;
2. proposal body;
3. decision state;
4. readiness summary;
5. structured contributions;
6. narrative/imported artifacts;
7. artifact status summary;
8. grouped questions and next actions.

The output should be concise enough for owner review. Long artifacts can be
summarized or clipped using existing rendering conventions.

Displayed paths should be labeled as source/evidence paths, not edit targets.

## MCP Output Shape

MCP should return structured JSON-compatible data using the same service view.
It should not return only CLI-formatted text for the full view.

Schema/handler tests should assert the presence of stable fields such as
`artifact_status`, `questions`, `next_actions`, and public values for
expectation, status, materialization/provenance, and question group names.

If extending an existing show tool is simpler, add a `full` boolean argument. If
that would make the schema unclear, add a dedicated read-only full-view tool.

## Error Handling

- Unknown proposal IDs should produce the existing not-found behavior.
- Missing optional files should become artifact status entries, not exceptions.
- Missing required files should be visible in artifact status and, if current
  behavior already treats them as errors, continue to do so.
- Renderer failures should not trigger file writes or partial repairs.
- Readiness and artifact status disagreements should be rendered explicitly
  rather than coerced into one answer.

## Migration Strategy

No migration is required.

Legacy proposals are handled by lazy derivation:

- explicit artifact state is used when available;
- known physical files are mapped into the catalog;
- unknown provenance is reported conservatively;
- absent optional artifacts remain absent.
- explicit artifact state may be used when present, but missing or stale
  metadata must not invalidate the proposal by itself.

## Test Strategy

Use service tests for view-model completeness and edge cases. Use CLI tests only
for public output contracts. Use MCP tests for schema and read-only payload
shape.

Focused tests:

- artifact catalog with reduced-footprint proposal;
- artifact catalog with legacy narrative files;
- artifact catalog with imported artifacts;
- full view includes all decision-relevant sections;
- full view separates structured owner questions, analytical open-question
  contributions, and legacy narrative question artifacts;
- default show output remains stable;
- MCP full view matches service-level concepts;
- MCP schemas expose stable structured fields and public values;
- read operations do not create files and preserve existing file contents;
- artifact status and readiness may disagree without either mutating or
  overriding the other;
- long narrative artifacts are summarized or clipped in owner-facing output.

## Risks And Mitigations

### Full view becomes too noisy

Mitigation: render summaries and stable section headers, not every raw file in
full.

### Provenance is not always knowable

Mitigation: expose `legacy` or `unknown` instead of guessing.

### Artifact status duplicates readiness

Mitigation: keep artifact status descriptive and readiness evaluative.

### CLI/MCP drift

Mitigation: build one service view model and test both surfaces against it.

### Paths look like edit instructions

Mitigation: label paths as source/evidence hints and keep next actions pointed
at P2P commands or explicit write-safe MCP tools.

### Question-like sources are conflated

Mitigation: group structured owner questions, analytical open-question
contributions, and legacy narrative question artifacts separately.
