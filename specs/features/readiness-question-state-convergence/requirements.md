# Requirements - Readiness Question State Convergence

## Scope

Correct proposal-level readiness so owner-question resolution is computed from
structured proposal question state when that state exists.

The current readiness path can still treat historical or narrative
`open-questions.md` bullets as unresolved owner input even after
`questions.yml` records those questions as answered, applied, retired,
superseded, muted, or deferred. This feature makes the structured lifecycle the
authoritative source for readiness question state and keeps markdown question
text as human-readable evidence or legacy fallback.

## Origin

- Source proposal: `PROP-089 - Readiness Question-State Convergence`.
- Local planning context: owner discussion confirmed that this concerns
  per-proposal readiness, not whole-project readiness.
- Local implementation layer: this spec lives under `specs/` and must not write
  implementation tasks or branch state into `.p2p/`.
- Governance note: `PROP-089` was still draft/pending when this local feature
  spec was prepared. Runtime implementation should proceed only after explicit
  owner confirmation that this is the selected direction.

## In Scope

- Proposal-level readiness owner-question resolution.
- Evidence-aware readiness assessment behavior.
- Conservative legacy fallback for proposals without `questions.yml`.
- Structured classification of owner questions into blocking, answered but not
  applied, residual follow-up, closed, and confidence-only categories.
- Readiness explain/review output that reports the source used and exact
  structured question categories.
- Focused service, CLI, MCP, and persistence tests for observable behavior.
- Documentation updates if public CLI/MCP readiness output changes.

## Out Of Scope

- Whole-project readiness or project maturity scoring.
- Proposal acceptance, rejection, defer, merge, or governance decisions.
- Changing owner override authority.
- Replacing `open-questions.md` or migrating historical proposals.
- Turning the agent interview flow into a batch questionnaire.
- Adding new question states to the persisted `questions.yml` schema in the
  first implementation slice.
- Reworking artifact-state policy, impact-map scoring, or readiness profile
  thresholds.
- Broad refactoring of CLI, MCP, storage, or proposal services unrelated to
  readiness question semantics.

## Functional Requirements

- R001: WHEN a proposal has a valid `questions.yml`, THE SYSTEM SHALL use that
  structured question state as the authoritative source for
  `owner_questions_resolution`.
- R002: WHEN a proposal does not have `questions.yml`, THE SYSTEM SHALL preserve
  the current `open-questions.md` markdown fallback for detecting unresolved
  owner questions.
- R003: WHEN `questions.yml` exists, THE SYSTEM SHALL NOT treat
  `open-questions.md` question bullets as blocking owner input.
- R004: WHEN a high-priority structured question is in state `to_answer` and its
  group is not muted or deferred, THE SYSTEM SHALL classify it as a blocking
  owner question.
- R005: WHEN a structured question is in state `answered`, THE SYSTEM SHALL NOT
  classify it as missing owner input and SHALL classify it as
  `answered_not_applied` until it is applied or otherwise closed.
- R006: WHEN a structured question is in state `applied`, `retired`, or
  `superseded`, THE SYSTEM SHALL classify it as closed for owner-question
  readiness.
- R007: WHEN a structured question or its group is in state `muted` or `defer`,
  THE SYSTEM SHALL NOT classify it as a blocking owner question.
- R008: WHEN a deferred structured question is relevant to readiness, THE SYSTEM
  SHALL surface it as a confidence note or caution rather than a hard blocker.
- R009: WHEN a medium- or low-priority structured question remains unresolved,
  THE SYSTEM SHALL surface it as residual follow-up by default unless an
  explicit readiness policy marks that priority as blocking.
- R010: WHEN readiness is assessed from structured question state, THE SYSTEM
  SHALL persist or expose enough evidence to identify the source used, blocking
  owner questions, answered-not-applied questions, residual follow-up, closed
  questions, and confidence notes.
- R011: WHEN readiness explain or review is requested, THE SYSTEM SHALL report
  exact structured question IDs and categories instead of only generic
  owner-question gates.
- R012: WHEN owner override is recorded, THE SYSTEM SHALL preserve the computed
  readiness truth and SHALL NOT rewrite unresolved structured questions as
  resolved.
- R013: WHEN the next-question workflow is used, THE SYSTEM SHALL continue to
  select only the next eligible `to_answer` question according to existing
  priority and muted/deferred group rules.
- R014: IF a future schema introduces an explicit `reopened` question state,
  THEN THE SYSTEM SHALL treat reopened high-priority questions like `to_answer`;
  this feature SHALL NOT introduce that schema change without a separate
  explicit decision.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep readiness question classification in service or
  domain helper code, not in Typer command handlers or MCP transport handlers.
- N002: THE SYSTEM SHALL preserve existing public command names, MCP tool names,
  and compatible response fields.
- N003: THE SYSTEM SHALL add fields or output sections in a backward-compatible
  way when richer readiness explanation is needed.
- N004: THE SYSTEM SHALL keep `P2PWorkspace` as a compatibility facade with
  delegation only.
- N005: THE SYSTEM SHALL not mutate proposal question state from read-only
  readiness show/explain/review/list operations.
- N006: THE SYSTEM SHALL validate `questions.yml` through existing question
  validation before using it as readiness evidence.
- N007: THE SYSTEM SHALL test observable behavior through service, CLI, MCP, and
  persisted readiness artifact paths where public behavior is affected.
- N008: THE SYSTEM SHALL avoid broad refactoring and behavior changes in the same
  implementation slice unless the owner explicitly approves the combined scope.

## Edge Cases And Errors

- E001: `questions.yml` exists and all high-priority questions are `applied`,
  while `open-questions.md` still contains stale question bullets.
- E002: `questions.yml` exists and a high-priority question is `to_answer`.
- E003: `questions.yml` exists and a high-priority question is `answered` but
  not applied.
- E004: `questions.yml` exists and a high-priority question is `retired`.
- E005: `questions.yml` exists and a high-priority question is `superseded`.
- E006: `questions.yml` exists and a high-priority question is `muted`.
- E007: `questions.yml` exists and a high-priority question group is `muted`.
- E008: `questions.yml` exists and a high-priority question or group is
  `defer`.
- E009: `questions.yml` exists and only medium/low `to_answer` questions remain.
- E010: `questions.yml` is absent and `open-questions.md` contains markdown
  question bullets.
- E011: `questions.yml` is invalid according to the existing schema validator.
- E012: owner override exists while structured unresolved questions remain.
- E013: readiness review is requested for a proposal with initialized question
  state and no blocking questions.
- E014: readiness explain/list gaps is requested through MCP and must preserve
  existing top-level payload compatibility.

## Acceptance Criteria

- AC001: Service tests prove `questions.yml` suppresses stale
  `open-questions.md` blockers when structured questions are closed.
- AC002: Service tests prove high-priority `to_answer` questions block
  owner-question readiness by default.
- AC003: Service tests prove `answered` questions are reported as
  answered-not-applied and do not count as missing owner input.
- AC004: Service tests prove `applied`, `retired`, and `superseded` questions
  are closed for owner-question readiness.
- AC005: Service tests prove `muted` and `defer` question or group states are
  non-blocking and produce appropriate caution/confidence evidence when needed.
- AC006: Service tests prove medium/low unresolved questions are residual
  follow-up by default and do not create hard owner-question gates.
- AC007: Legacy tests prove proposals without `questions.yml` still use the
  markdown fallback.
- AC008: CLI tests prove readiness assess/explain output no longer reports
  stale markdown owner-question blockers when structured questions are resolved.
- AC009: MCP tests prove readiness assess/explain/list-gaps payloads include
  structured question evidence while preserving existing fields.
- AC010: Review tests prove `review_proposal_readiness` reports exact blocking
  question IDs and does not suggest re-asking applied questions.
- AC011: Override tests prove owner override fields remain separate from the
  computed readiness state.
- AC012: Existing readiness, proposal question, CLI, MCP, validation, and full
  test suites continue to pass.
