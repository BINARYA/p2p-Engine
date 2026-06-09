# Implementation Note - Boundaries

Reviewed before implementation:

- `src/p2p_engine/services/readiness.py`
- `src/p2p_engine/services/proposals.py`
- `src/p2p_engine/storage/filesystem.py`
- `src/p2p_engine/cli_commands/proposal_readiness.py`
- `src/p2p_engine/cli_commands/proposals.py`
- `src/p2p_engine/services/validation.py`
- existing readiness and CLI tests

Implementation boundary:

- Put question lifecycle domain behavior in a new
  `ProposalQuestionService`.
- Put typed records and enums in `core/proposal_questions.py`.
- Keep `P2PWorkspace` as compatibility facade with delegation only.
- Keep Typer command modules as presentation/orchestration only.
- Extend readiness refresh with additive guidance only; do not change existing
  score semantics.
- Treat aggregation as advisory in this slice.
- Treat missing question state as normal backward-compatible state.

Do not add new question lifecycle domain logic directly to `cli.py`,
`storage/filesystem.py`, or `mcp/tools.py`.

## Second Slice

Implemented after the refined second acceptance of `PROP-082`:

- `proposal questions apply` now returns an artifact-aware update plan and
  stores the plan on applied questions.
- `proposal readiness assess` performs evidence-aware recalculation from current
  artifacts and question state while `refresh` remains conservative.
- Readiness review emits stepped assertiveness guidance for weak, partial,
  residual, and confirmation modes.
- Readiness review reports advisory duplicate/aggregation candidates without
  changing proposal decisions.
- Agent instructions and docs now direct agents to apply answers to artifacts
  and run `p2p proposal readiness assess` after refinement.

Focused verification:

```text
.venv/bin/pytest tests/test_readiness_service.py tests/test_proposal_questions_service.py \
  tests/test_cli.py::test_cli_proposal_questions_lifecycle_and_refresh_guidance \
  tests/test_mcp.py::test_mcp_proposal_question_tools_are_write_safe
8 passed
```

Final verification:

```text
.venv/bin/p2p proposal readiness assess PROP-082
computed_score: 100
computed_label: decision_ready
confidence: high
```

```text
.venv/bin/p2p validate
errors: 0
warnings: 0
infos: 0
findings: none
```

```text
.venv/bin/pytest
381 passed in 62.98s
```
