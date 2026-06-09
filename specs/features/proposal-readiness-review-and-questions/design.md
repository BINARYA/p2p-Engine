# Design - Proposal Readiness Review And Questions

## Requirements Covered

- R001-R020
- N001-N007
- E001-E008

## Key Decisions

- D001: Add a dedicated `ProposalQuestionService`.
  Rationale: question lifecycle, audit, grouping, next-question selection, and
  answer application are cohesive domain behavior. Keeping this in a service
  preserves the `P2PWorkspace` compatibility facade and avoids adding domain
  logic directly to CLI, MCP handlers, or `storage/filesystem.py`.

- D002: Keep `ReadinessService.refresh` conservative and add separate
  evidence-aware review/assess behavior.
  Rationale: refresh is already public behavior. Changing it into qualitative
  review would make score changes harder to explain. Refresh should synchronize
  deterministic fields and point users to review/interview when needed.

- D003: Store proposal question state as structured YAML beside proposal state.
  Rationale: questions are proposal-scoped governance-adjacent memory. They need
  stable IDs, diffable text, validation, and backward-compatible absence.

- D004: Make agent proactivity an explicit generated-instructions behavior.
  Rationale: storage alone cannot cause better agent behavior. Agents need
  explicit instructions to ask questions, respect question state, and avoid
  passive summaries.

- D005: Treat aggregation as advisory until owner-controlled primitives exist.
  Rationale: detecting overlap is safe as analysis. Closing or aggregating
  proposals is governance and must not happen autonomously.

- D006: Add artifact-aware apply plans without automatically rewriting every
  artifact in the second slice.
  Rationale: a reliable multi-artifact update plan is needed before autonomous
  content rewriting. The command can mark answers applied once it has produced a
  deterministic plan and recorded that no governance mutation was performed.

- D007: Add `proposal readiness assess` as evidence-aware recalculation while
  keeping `refresh` conservative.
  Rationale: `refresh` is public compatibility behavior. `assess` can rebuild
  criterion evidence from current artifacts, question state, and owner-question
  state, then promote confidence when explicit evidence supports it.

- D008: Represent pedantry as stepped assertiveness guidance derived from
  readiness state.
  Rationale: readiness score, confidence, failed gates, missing items, and
  question states are enough to drive behavior without a separate index.

## Components

- `src/p2p_engine/core/proposal_questions.py`
  - Dataclasses/enums for question state, group state, priority, question
    records, question sets, question status, and operation results.

- `src/p2p_engine/services/proposal_questions.py`
  - Owns question state validation, read/write, init, add, answer, defer, mute,
    reopen, retire, supersede, group state updates, next-question selection,
    reassessment helpers, and apply summaries.

- `src/p2p_engine/services/readiness.py`
  - Keeps profile/readiness refresh behavior.
  - Adds review/assess result structures or delegates review assembly to a
    dedicated readiness-review helper if it grows beyond scoring concerns.
  - Emits refresh guidance when question state or weak readiness implies that
    review/interview is needed.

- `src/p2p_engine/services/proposals.py`
  - Remains proposal document/contribution owner.
  - Provides existing proposal update behavior used by question answer
    application. Do not duplicate proposal Markdown parsing here.

- `src/p2p_engine/services/agent_templates.py`
  - Adds explicit proactive readiness interview guidance and command examples.

- `src/p2p_engine/storage/filesystem.py`
  - Keeps public `P2PWorkspace` facade methods and delegates to services:
    `read_proposal_questions`, `initialize_proposal_questions`,
    `add_proposal_question`, `answer_proposal_question`,
    `set_proposal_question_state`, `next_proposal_question`,
    `reassess_proposal_questions`, `apply_proposal_question_answers`,
    and readiness review methods.

- `src/p2p_engine/cli_commands/proposal_questions.py`
  - Registers `p2p proposal questions ...` commands.
  - Handles Typer options and Rich/plain output only.

- `src/p2p_engine/cli_commands/proposal_readiness.py`
  - Adds `assess` or `review` command and improves refresh guidance output.

- `src/p2p_engine/mcp/catalog/proposals.py`
  - Adds question read/write tools and readiness review tools with explicit
    read/write descriptions.

- `src/p2p_engine/mcp/handlers/proposals.py`
  - Thin dispatch to workspace facade methods.

- `src/p2p_engine/services/validation.py`
  - Validates question state files.

- `src/p2p_engine/services/registry_records.py` and `services/registries.py`
  - Optional later slice: include compact question status in registries only if
    needed by `p2p context` or `p2p next`.

## Data And Contracts

Question state should be versioned:

```yaml
proposal_questions:
  schema_version: 1
  proposal_id: PROP-XXX
  initialized_at: "2026-06-08"
  updated_at: "2026-06-08"
  groups:
    - id: QG001
      gap: alternatives_quality
      state: to_answer
      priority: high
      rationale: "Alternatives are missing from readiness review."
  questions:
    - id: Q001
      group_id: QG001
      gap: alternatives_quality
      criterion: alternatives_quality
      priority: high
      state: to_answer
      question: "Which alternative should be considered first?"
      rationale: "Needed to improve alternatives_quality."
      answer: ""
      answer_source: ""
      answered_at: ""
      asked_count: 0
      last_asked_at: ""
      derived_from: []
      superseded_by: ""
      muted_reason: ""
      deferred_reason: ""
      applied_to_proposal: false
      applied_at: ""
      audit:
        created_by: local
        created_at: "2026-06-08"
        updated_by: local
        updated_at: "2026-06-08"
      apply_plan:
        - artifact: proposal.md
          action: update_acceptance_criteria
          status: deferred
          reason: "Requires explicit proposal update/import."
```

Allowed question states:

- `to_answer`
- `defer`
- `muted`
- `answered`
- `applied`
- `retired`
- `superseded`

Allowed priorities:

- `high`
- `medium`
- `low`

Read commands should return a `not_initialized` status when the file is absent.
Validation should accept absent state and reject malformed present state.

## CLI Surface

Initial CLI target:

```bash
p2p proposal questions init PROP-XXX
p2p proposal questions status PROP-XXX
p2p proposal questions list PROP-XXX
p2p proposal questions add PROP-XXX --gap GAP --priority high --question TEXT
p2p proposal questions answer PROP-XXX Q001 TEXT
p2p proposal questions defer PROP-XXX Q001 --reason TEXT
p2p proposal questions mute PROP-XXX Q001 --reason TEXT
p2p proposal questions reopen PROP-XXX Q001
p2p proposal questions group-status PROP-XXX QG001 --state to_answer|defer|muted
p2p proposal questions next PROP-XXX
p2p proposal questions reassess PROP-XXX
p2p proposal questions apply PROP-XXX
p2p proposal questions import PROP-XXX FILE
p2p proposal readiness assess PROP-XXX
p2p proposal readiness review PROP-XXX
```

`assess` may be used instead of `review` if final CLI naming prefers existing
assessment terminology. Do not expose both unless aliases are deliberately
tested and documented.

## Readiness Review Flow

1. Read proposal detail, contributions, readiness state, and question state.
2. If question state is absent and readiness is weak, return proactive guidance
   to initialize questions.
3. For each missing readiness criterion, emit evidence, owner questions,
   challenge points, and acceptance cautions.
4. Update readiness review fields only when evidence is explicit.
5. Keep computed scores conservative when evidence is absent.
6. Report commands to continue: question next/answer/apply/reassess or
   readiness review.

## Evidence-Aware Assessment Flow

1. Re-read current proposal artifacts and question state.
2. Recompute criterion quality from current artifact content.
3. Treat resolved open questions and applied question answers as evidence for
   owner-question resolution.
4. Promote confidence to `medium` when there are no missing criteria, no failed
   gates, no unresolved owner questions, and no unanswered high-priority
   questions.
5. Promote confidence to `high` only when the score is decision-ready and no
   question workflow is pending.
6. Emit stepped assertiveness guidance:
   - weak/blocked: aggressive interview, no acceptance recommendation;
   - partial: focused follow-up on high-impact gaps;
   - strong/near target: residual confirmation;
   - decision-ready: concise confirmation and owner decision reminder.

## Agent Guidance Contract

Generated instructions should tell agents:

- inspect readiness before recommending acceptance;
- if weak, initialize or resume question workflow;
- ask one focused question at a time;
- record answers through CLI/MCP, not only chat memory;
- after each answer, reassess remaining questions;
- respect `defer` and `muted`;
- use answered questions to refine proposal text through supported commands;
- re-run readiness review/refresh and report remaining gaps;
- distinguish computed score from owner override;
- propose aggregation for duplicate proposals but never decide it.
- when readiness is low, do the next workflow step instead of only summarizing:
  initialize/update questions, ask the next focused question, record the answer,
  apply it, and run evidence-aware assessment.

## Error Handling

- Missing question state: return normal `not_initialized` status.
- Unknown proposal: reuse existing proposal lookup errors.
- Unknown question: error with proposal ID, question ID, and recovery hint.
- Invalid state transition: error with current state and allowed transitions.
- Malformed YAML: validation error naming the path and invalid field.
- Apply without answered questions: report no actionable answers.
- Governance boundary violation: stop and name the owner-controlled command or
  decision required.

## Migration And Compatibility

- Existing proposals do not need question state files.
- Existing readiness files remain valid.
- Existing `proposal readiness show/init/refresh/explain` commands retain
  current behavior and output shape except for additive guidance.
- New question state validation must treat missing files as valid.
- Registry refresh must not require question files.
- MCP tools must be additive.

## Risks And Tradeoffs

- More CLI surface area increases maintenance cost.
  Mitigation: centralize lifecycle behavior in `ProposalQuestionService` and
  keep CLI/MCP thin.

- Agent guidance could become too aggressive.
  Mitigation: support `defer` and `muted`, while keeping proactivity as default.

- Applying answers to proposal text can become ambiguous.
  Mitigation: first implementation may produce a structured apply summary or
  require explicit fields/sections before updating proposal text.

- Duplicate/aggregation handling can cross governance boundaries.
  Mitigation: keep detection advisory until explicit owner-controlled
  aggregation primitives exist.

## Out Of Scope

- Provider-hosted review workflows.
- Autonomous proposal acceptance or cleanup.
- Full semantic duplicate detection with embeddings or external AI.
- Rewriting project-level maturity assessment.
