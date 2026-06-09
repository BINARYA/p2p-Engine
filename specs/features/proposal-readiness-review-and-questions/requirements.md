# Requirements - Proposal Readiness Review And Questions

## Scope

Define the production-ready local development requirements for the accepted
PROP-082 direction: evidence-aware proposal readiness review, first-class
proposal question memory, proactive agent interview guidance, refresh guidance,
and duplicate/aggregation detection.

## Origin

- Source proposal: PROP-082 - Readiness Assessment Refresh And Review Workflow
- Decision: accepted with explicit readiness override
- Related proposals: PROP-002, PROP-054, PROP-055, PROP-056, PROP-081
- Existing baseline spec: `specs/features/proposal-readiness-and-prompts`

## In Scope

- First-class proposal question/interview state managed by CLI and service APIs.
- Question and question-group lifecycle commands.
- Evidence-aware readiness review/assess workflow distinct from conservative
  readiness refresh.
- Proactive agent guidance outputs for weak proposals.
- Backward-compatible behavior when question state is absent.
- Duplicate/overlap/aggregation candidate reporting for proposals.
- Tests for storage, CLI, readiness, agent-template, and MCP behavior where
  public surfaces are added.

## Out Of Scope

- Autonomous proposal acceptance, rejection, deferral, aggregation closure, or
  governance override by agents.
- Direct AI-provider calls from P2P Engine.
- Replacing existing `proposal readiness refresh`, `show`, `init`, or `explain`
  semantics.
- Full project-level assessment redesign. This feature is proposal-level.
- Raw Git or provider PR/MR automation.

## Functional Requirements

- R001: WHEN a proposal has no question state, THE SYSTEM SHALL report the
  absence as normal state without raising an error.
- R002: WHEN requested, THE SYSTEM SHALL initialize deterministic question state
  for a proposal without changing proposal decision status.
- R003: WHEN a question is added, THE SYSTEM SHALL assign a stable proposal-local
  question ID and persist the question with an initially empty answer.
- R004: WHEN a question is added, THE SYSTEM SHALL require or derive a readiness
  gap or criterion link, priority, state, rationale, and audit metadata.
- R005: WHEN a question is listed or shown, THE SYSTEM SHALL expose question ID,
  group ID when present, gap, priority, state, answer state, and applied state.
- R006: WHEN an answer is recorded, THE SYSTEM SHALL persist answer text, answer
  source, answered timestamp, and transition the question to `answered`.
- R007: WHEN a question is deferred, muted, reopened, retired, superseded, or
  applied, THE SYSTEM SHALL preserve audit metadata and not lose the original
  question or answer text.
- R008: WHEN a question group state is changed, THE SYSTEM SHALL apply re-ask
  behavior deterministically to the group while preserving individual question
  audit records.
- R009: WHEN the next question is requested, THE SYSTEM SHALL return the highest
  priority eligible `to_answer` question after excluding deferred, muted,
  retired, superseded, applied, and already answered questions unless explicitly
  requested.
- R010: WHEN readiness is weak, below threshold, low-confidence, or blocked by
  owner input, THE SYSTEM SHALL provide agent guidance to initialize or resume
  the question interview proactively.
- R011: WHEN an answer is recorded, THE SYSTEM SHALL support reassessing whether
  existing questions remain valid, should be superseded, should be retired, or
  require follow-up questions.
- R012: WHEN requested, THE SYSTEM SHALL apply answered question content to the
  proposal through supported proposal update/import behavior and mark applied
  questions as applied.
- R013: WHEN applying answers would change governance decisions, THE SYSTEM
  SHALL stop and require owner-controlled governance commands instead.
- R014: WHEN `proposal readiness refresh` is run, THE SYSTEM SHALL keep refresh
  deterministic and conservative while emitting actionable guidance if
  qualitative reassessment or question workflow is needed.
- R015: WHEN evidence-aware review/assess is run, THE SYSTEM SHALL read proposal
  artifacts, contributions, readiness state, and question state to update
  criterion evidence, missing items, failed gates, confidence, owner questions,
  suggested next actions, and behavioral guidance outputs.
- R016: WHEN evidence-aware review/assess cannot resolve a criterion
  deterministically, THE SYSTEM SHALL leave the computed score conservative and
  emit focused owner questions instead of inventing evidence.
- R017: WHEN duplicate or mergeable proposals are detected, THE SYSTEM SHALL
  report merge candidates and ask for owner direction without closing either
  proposal autonomously.
- R018: WHEN owner-approved aggregation is performed through supported future
  primitives, THE SYSTEM SHALL preserve transferred content provenance and mark
  the superseded proposal with an explicit aggregation trace.
- R019: WHEN agent-facing instructions are generated, THE SYSTEM SHALL instruct
  agents to be proactive by default for weak proposal readiness, ask one focused
  question at a time, respect defer/muted states, and avoid recommending
  acceptance while methodological gaps remain.
- R020: WHEN MCP tools are added for question or readiness review behavior, THE
  SYSTEM SHALL mark read/write behavior explicitly and keep governance decisions
  permission-gated or owner-controlled.
- R021: WHEN readiness review or question generation evaluates a proposal, THE
  SYSTEM SHALL consider the full proposal artifact set, including proposal text,
  exploration artifacts, impact/overlap artifacts, readiness state, question
  state, and aggregation evidence.
- R022: WHEN answered questions are applied, THE SYSTEM SHALL return an
  artifact-aware update plan naming affected artifacts, intended action, and
  whether each update is applied, deferred, or not needed.
- R023: WHEN readiness assessment is requested after artifact refinement, THE
  SYSTEM SHALL recompute criterion evidence from current artifacts and promote
  confidence when no missing criteria, failed gates, unresolved owner questions,
  or unanswered high-priority questions remain.
- R024: WHEN readiness is weak, gate-blocked, low-confidence, or below target,
  THE SYSTEM SHALL emit stepped assertiveness guidance that directs agents to
  continue the interview instead of passively reporting gaps.
- R025: WHEN readiness is partial or near target, THE SYSTEM SHALL reduce
  assertiveness to focused follow-up or residual confirmation while respecting
  deferred and muted question/group state.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL preserve public CLI compatibility for existing
  readiness commands.
- N002: THE SYSTEM SHALL store question state in structured project files under
  managed proposal state only through P2P service/CLI/MCP write primitives.
- N003: THE SYSTEM SHALL validate question state and reject malformed state with
  actionable diagnostics.
- N004: THE SYSTEM SHALL use atomic file writes for persisted question and
  readiness review state.
- N005: THE SYSTEM SHALL keep domain behavior in services; CLI and MCP handlers
  SHALL remain thin orchestration and presentation layers.
- N006: THE SYSTEM SHALL avoid broad registry, proposal, or Git scans unless a
  command explicitly needs overlap analysis.
- N007: THE SYSTEM SHALL preserve owner override metadata without falsifying
  computed readiness scores.

## Edge Cases And Errors

- E001: Missing question state returns `not_initialized` or equivalent status.
- E002: Unknown question IDs produce an actionable error naming the proposal and
  missing question.
- E003: Invalid question states, priorities, timestamps, group states, or
  malformed YAML produce validation errors.
- E004: Answering an already answered question requires either a replacement
  flag or a superseding follow-up question.
- E005: Applying answers when no answered/unapplied questions exist reports no
  actionable answers.
- E006: Muted questions are skipped by default but can be included with an
  explicit include-muted option.
- E007: Deferred questions are skipped by default but remain visible in status
  and list output.
- E008: Proposal aggregation candidates must never close proposals without an
  owner-controlled operation.

## Acceptance Criteria

- AC001: CLI tests prove missing question state is reported gracefully.
- AC002: CLI and service tests prove question init/add/list/answer/defer/mute/
  reopen/next/reassess/apply behavior.
- AC003: Tests prove question IDs are stable and audit metadata is preserved
  across state transitions.
- AC004: Tests prove refresh remains conservative while printing guidance toward
  assess/review and question commands when appropriate.
- AC005: Tests prove agent instructions include proactive readiness interview
  behavior and defer/muted handling.
- AC006: Tests prove readiness review consumes question state and emits owner
  questions, challenge points, acceptance cautions, and suggested next actions.
- AC007: Tests prove duplicate/aggregation candidates are reported without
  autonomous governance decisions.
- AC008: Validation tests prove malformed question state is detected.
- AC009: Existing readiness, proposal decision, registry, MCP, and validation
  tests remain passing.
- AC010: Tests prove `proposal questions apply` returns an artifact update plan
  for answered questions and marks them applied without mutating governance.
- AC011: Tests prove `proposal readiness assess` recalculates from current
  artifacts, can raise confidence, and emits stepped assertiveness guidance.
- AC012: Tests prove low-readiness review/assess instructs agents to ask the next
  focused question through question workflow commands.
