# Implementation Note - Readiness Question State Convergence

## Design Choice

Implemented a targeted readiness semantics fix inside
`src/p2p_engine/services/readiness.py`.

`questions.yml` is now the authoritative owner-question readiness source when
present and valid. `open-questions.md` remains markdown fallback for legacy
proposals without structured question state.

The implementation did not add a new persisted `reopened` question state. The
current schema remains unchanged.

## Framework / Project Convention Considered

- Kept readiness classification in `ReadinessService`.
- Kept `ProposalQuestionService` as the lifecycle owner for question mutation.
- Kept `P2PWorkspace` as a facade.
- Kept CLI and MCP handlers as presentation/transport layers.
- Preserved existing command names, MCP tool names, and top-level payload
  fields.

## Compatibility Impact

- Additive readiness data: `owner_question_state`.
- Additive CLI rendering in readiness `assess`, `explain`, and `review` output.
- Additive MCP fields under readiness payloads and explanation/gap payloads.
- No `questions.yml` schema migration.
- No change to proposal governance decisions or owner override authority.

## Behavior Changes

- Structured question state suppresses stale markdown false blockers.
- High-priority `to_answer` structured questions are hard owner-question
  blockers.
- `answered` questions are reported as `answered_not_applied` and do not count
  as missing owner input.
- `applied`, `retired`, and `superseded` questions are closed.
- `muted`, `defer`, and medium/low unresolved questions are non-blocking
  residual follow-up or confidence notes by default.
- Legacy proposals without `questions.yml` still use markdown fallback.
- Owner override remains separate from computed readiness truth.

## Files Changed

- `src/p2p_engine/services/readiness.py`
- `src/p2p_engine/cli_commands/proposal_readiness.py`
- `src/p2p_engine/mcp/handlers/proposals.py`
- `tests/test_readiness_service.py`
- `tests/test_cli.py`
- `tests/test_mcp.py`
- `docs/CLI-GUIDE.md`
- `docs/MCP.md`
- `docs/AGENT-INTEGRATION.md`
- `specs/features/readiness-question-state-convergence/tasks.md`

## Tests And Validation

Executed:

```bash
.venv/bin/pytest tests/test_readiness_service.py
.venv/bin/pytest tests/test_readiness_service.py tests/test_proposal_questions_service.py tests/test_cli.py::test_cli_readiness_assess_reports_structured_question_state tests/test_mcp.py::test_mcp_readiness_tools_include_structured_question_state
.venv/bin/pytest tests/test_cli.py tests/test_mcp.py
.venv/bin/p2p validate
.venv/bin/pytest
```

Observed results:

```text
tests/test_readiness_service.py: 13 passed
focused readiness/question/CLI/MCP: 17 passed
tests/test_cli.py tests/test_mcp.py: 155 passed
p2p validate: 0 errors, 0 warnings, 0 infos
full suite: 462 passed
```

## Risks

- The additive `owner_question_state` field increases payload size slightly for
  readiness responses.
- Legacy markdown fallback remains intentionally conservative and can still
  mark markdown-only proposals as owner-question blocked.

## Follow-Up

- A separate schema proposal is needed before introducing a persisted
  `reopened` question state.
- If future readiness policies need medium/low questions to block in selected
  contexts, add an explicit policy mechanism rather than hardcoding it in this
  feature.
