# Design - Readiness Question State Convergence

## Requirements Covered

- R001-R014
- N001-N008
- E001-E014
- AC001-AC012

## Key Decisions

- D001: Treat this as a targeted readiness semantics fix, not a readiness
  profile redesign.
  Rationale: the observed failure is source-of-truth convergence for
  owner-question state. Changing scoring weights, maturity thresholds, or
  impact-map scoring would mix unrelated behavior into the same change.

- D002: Use `questions.yml` as source of truth only when it exists and validates.
  Rationale: new proposals with structured question state should not be blocked
  by stale markdown. Historical proposals without structured state must keep
  the current markdown fallback to avoid forced migrations.

- D003: Do not add a persisted `reopened` state in the first slice.
  Rationale: the current schema supports `to_answer`, `defer`, `muted`,
  `answered`, `applied`, `retired`, and `superseded`. Reopening can be
  represented today by returning a question to `to_answer` or by superseding it
  with a new question. Adding a new schema value would be a compatibility
  change and needs a separate explicit decision.

- D004: Add a small structured question-readiness classification helper behind
  `ReadinessService`.
  Rationale: classification must be reused by initialize, assess, review, CLI,
  and MCP paths without duplicating state logic in presentation layers.

- D005: Keep read-only readiness operations read-only.
  Rationale: `show`, `explain`, `review`, and MCP list-gaps are inspection
  surfaces. They may display structured evidence already stored in
  `readiness.yml` or computed from current artifacts, but must not mutate
  `questions.yml`.

- D006: Preserve owner override as effective governance metadata, not computed
  truth.
  Rationale: the owner may proceed despite unresolved questions, but readiness
  must still report unresolved structured state truthfully.

- D007: Expose richer question evidence in a backward-compatible shape.
  Rationale: agents need exact question IDs and categories, but existing CLI/MCP
  callers depend on current top-level fields such as `failed_gates`, `missing`,
  and `suggested_next`.

## Components

- `src/p2p_engine/services/readiness.py`
  - Owns owner-question readiness classification.
  - Should read and validate `questions.yml` when present.
  - Should preserve markdown fallback when `questions.yml` is absent.
  - Should drive readiness `initialize`, `assess`, and `review` from the same
    classification result.

- `src/p2p_engine/core/proposal_questions.py`
  - Owns existing question states and priorities.
  - Should not gain a new `reopened` state in this feature unless a separate
    schema decision is made first.

- `src/p2p_engine/services/proposal_questions.py`
  - Owns question lifecycle state validation, next-question selection, and
    apply behavior.
  - Should remain the lifecycle owner; readiness consumes its persisted state
    but does not mutate it.

- `src/p2p_engine/storage/filesystem.py`
  - Remains the `P2PWorkspace` compatibility facade.
  - May receive delegation-only wiring if the readiness service return shape
    changes.

- `src/p2p_engine/cli_commands/proposal_readiness.py`
  - Presents readiness show/init/refresh/assess/explain/review output.
  - Should not decide owner-question categories; it should render service data.

- `src/p2p_engine/mcp/handlers/proposals.py`
  - Presents existing readiness MCP tool payloads.
  - Should preserve current fields and add structured explanation data only as
    backward-compatible payload extensions.

- `tests/test_readiness_service.py`
  - Primary service-level regression coverage for structured-vs-markdown
    readiness behavior.

- `tests/test_proposal_questions_service.py`
  - Lifecycle coverage for states consumed by readiness, especially group
    mute/defer behavior if additional regression coverage is needed.

- `tests/test_cli.py`
  - CLI observable behavior for readiness assess/explain/review.

- `tests/test_mcp.py`
  - MCP payload compatibility and structured evidence behavior.

- `docs/`
  - Public docs only if CLI/MCP readiness semantics or output sections change in
    a way users should rely on.

## Data And Contracts

### Question Readiness Summary

The readiness service should build a summary from proposal artifacts:

```text
source: structured | markdown_fallback | none
markdown_fallback_used: true | false
blocking_owner_questions: list[question_ref]
answered_not_applied: list[question_ref]
residual_follow_up: list[question_ref]
closed_questions: list[question_ref]
confidence_notes: list[str]
```

Each `question_ref` should include at least:

```text
id
group_id
priority
state
criterion/gap
reason
```

If the summary is persisted in `readiness.yml`, it should be optional and
backward-compatible. Validation currently allows additional readiness fields;
the implementation should keep that compatibility and avoid requiring historical
readiness files to contain the new section.

### Structured State Classification

When `questions.yml` exists:

- `high + to_answer + active group` -> `blocking_owner_questions`
- `answered` -> `answered_not_applied`
- `medium/low + to_answer + active group` -> `residual_follow_up`
- `applied`, `retired`, `superseded` -> `closed_questions`
- question or group `muted` -> non-blocking confidence note or closed/caution
- question or group `defer` -> non-blocking confidence note or residual caution

The current schema does not include `reopened`. If a future schema adds it,
classification should treat `high + reopened` like `high + to_answer`.

### Markdown Fallback

When `questions.yml` is absent:

- keep existing `open-questions.md` fallback behavior;
- continue using `count_open_questions` or an equivalent helper;
- mark summary source as `markdown_fallback`;
- do not require migration to structured questions.

### Readiness Score Interaction

Owner-question readiness should affect the existing criterion, not create a new
score profile:

- blocking structured questions may keep `owner_questions_resolution` as
  `needs_owner_input` or otherwise produce failed owner-question gates;
- answered-not-applied questions should not count as missing owner input, but
  should produce suggested next action or confidence caution;
- residual medium/low questions should reduce confidence or appear in
  suggestions by default, not hard-block decision readiness;
- closed structured questions should allow evidence-aware assessment to promote
  artifacts when no other blockers exist.

### Public Output

CLI and MCP should keep existing fields:

```text
computed_score
computed_label
confidence
failed_gates
missing
suggested_next
```

They may add structured explanation fields, for example:

```text
owner_question_state
blocking_owner_questions
answered_not_applied
residual_follow_up
confidence_notes
markdown_fallback_used
```

Existing tests and downstream consumers should not have to remove or rename
current fields.

## Error Handling

- Invalid `questions.yml` should fail through the existing question validation
  path with actionable diagnostics.
- Absence of `questions.yml` is not an error and should use markdown fallback.
- Absence of `open-questions.md` when `questions.yml` exists is not an error.
- Read-only explain/review/list operations must not repair or rewrite invalid
  question state.
- Owner override must not hide unresolved structured categories.

## Migration And Compatibility

- No migration is required for proposals without `questions.yml`.
- No persisted schema version bump is required if the implementation only adds
  optional readiness evidence fields.
- Existing public CLI command names and MCP tool names remain unchanged.
- Existing `ProposalQuestionState` values remain unchanged in the first slice.
- Existing `P2PWorkspace` method names and return shape compatibility should be
  preserved; richer fields may be additive.
- If a future implementation requires required readiness fields or a new
  question state, create a separate schema/migration spec before coding it.

## Test Strategy

- Start with failing service regression tests that reproduce the current
  behavior: applied structured high-priority questions plus stale markdown still
  keep readiness below decision-ready.
- Add focused tests for every question-state category.
- Add legacy fallback tests proving markdown-only proposals still behave as
  before.
- Add CLI tests only for user-visible output changes.
- Add MCP tests only for payload compatibility and structured evidence.
- Run focused tests first, then broader readiness/question/CLI/MCP tests, then
  the full suite before marking implementation complete.

## Risks And Tradeoffs

- Risk: medium/low unresolved questions may be treated too permissively.
  Mitigation: keep them visible as residual follow-up and allow future policy to
  mark them blocking.
- Risk: adding explanation fields could accidentally become a breaking MCP
  payload change.
  Mitigation: make fields additive and preserve existing keys.
- Risk: readiness logic may duplicate proposal question lifecycle rules.
  Mitigation: consume validated question state and keep lifecycle mutations in
  `ProposalQuestionService`.
- Risk: changing `initialize` and `assess` together may hide behavior drift.
  Mitigation: test both paths separately and keep the classification helper
  small and pure.
- Risk: current score promotion is coupled to the global blocker calculation.
  Mitigation: isolate the blocker decision behind structured summary and cover
  promotion behavior with regression tests.

## Out Of Scope

- Project-wide assessment changes.
- Readiness profile score weight changes.
- Impact-map quality promotion changes.
- New proposal governance decisions.
- New MCP tools.
- New CLI commands.
- Question schema migration to add `reopened`.
- Broad readiness service extraction or CLI/MCP module splitting.
