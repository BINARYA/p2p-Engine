# Tasks - Readiness Question State Convergence

- [x] T001: Review current readiness/question implementation and confirm the
  implementation boundary in a short code note or PR summary; completion is a
  documented boundary that names `ReadinessService`, `ProposalQuestionService`,
  CLI readiness commands, MCP proposal handlers, and affected tests. Covers
  N001-N008, D001-D005.

- [x] T002: Add a service regression test where `questions.yml` contains only
  applied high-priority questions and `open-questions.md` still contains stale
  question bullets; completion is a failing test before implementation or a
  passing test after the fix. Covers R001-R003, E001, AC001.

- [x] T003: Add service tests for high-priority `to_answer` questions with an
  active group; completion is readiness reporting a blocking owner question
  with exact question ID evidence. Covers R004, E002, AC002.

- [x] T004: Add service tests for high-priority `answered` questions; completion
  is readiness reporting `answered_not_applied` without missing-owner-input
  gates. Covers R005, E003, AC003.

- [x] T005: Add service tests for `applied`, `retired`, and `superseded`
  questions; completion is readiness treating each as closed and not counting
  stale markdown as a blocker. Covers R006, E001, E004-E005, AC004.

- [x] T006: Add service tests for question-level and group-level `muted` and
  `defer` states; completion is non-blocking readiness with confidence notes or
  cautions where applicable. Covers R007-R008, E006-E008, AC005.

- [x] T007: Add service tests for medium/low `to_answer` questions; completion
  is residual follow-up evidence without hard failed gates by default. Covers
  R009, E009, AC006.

- [x] T008: Add legacy fallback tests for proposals without `questions.yml`;
  completion is markdown-only `open-questions.md` behavior matching the current
  fallback. Covers R002, E010, AC007.

- [x] T009: Add validation/error-path tests for invalid `questions.yml`;
  completion is readiness assessment refusing invalid structured question state
  through existing validation diagnostics. Covers N006, E011.

- [x] T010: Introduce a small internal question-readiness summary helper in
  `src/p2p_engine/services/readiness.py`, or an adjacent service-owned helper if
  extraction is clearer; completion is a pure classification path with no
  writes and no CLI/MCP formatting. Covers R001-R010, N001, D004.

- [x] T011: Wire readiness initialization to use the question-readiness summary
  for `owner_questions_resolution`; completion is `initialize` using structured
  state when present and markdown fallback only when absent. Covers R001-R006,
  R010, D002, D004.

- [x] T012: Wire evidence-aware readiness assessment to use the same summary for
  blocker detection and confidence reasons; completion is no stale
  `Pending high-priority proposal questions remain` reason when all structured
  high-priority questions are applied. Covers R001-R010, D004, AC001-AC007.

- [x] T013: Preserve owner override semantics while structured unresolved
  questions remain visible; completion is tests proving override fields remain
  separate from computed readiness and question categories. Covers R012, E012,
  AC011.

- [x] T014: Extend readiness read/explain data structures in a
  backward-compatible way if needed for exact question evidence; completion is
  existing readiness fields preserved and additive structured evidence available
  to CLI/MCP/review. Covers R010-R011, N002-N003, D007.

- [x] T015: Update `review_proposal_readiness` to report exact structured
  blocking questions, answered-not-applied questions, residual follow-up, and
  markdown fallback usage; completion is review tests proving it does not
  suggest re-asking applied questions. Covers R011, R013, E013, AC010.

- [x] T016: Update CLI readiness rendering only as needed to expose additive
  structured evidence in `assess`, `explain`, or `review`; completion is CLI
  tests preserving current output and proving stale markdown blockers disappear
  when structured questions are resolved. Covers R011, N002-N003, E001, AC008.

- [x] T017: Update MCP proposal readiness handler payloads only as needed to
  expose additive structured evidence; completion is MCP tests preserving
  existing keys and proving structured evidence is available. Covers R011,
  N002-N003, E014, AC009.

- [x] T018: Confirm `next_proposal_question` behavior remains one-question-at-a
  time and unchanged by readiness assessment; completion is existing or new
  proposal-question tests covering priority, muted, and deferred group behavior.
  Covers R013, D005.

- [x] T019: Update public docs or agent-facing guidance if CLI/MCP readiness
  output gains new structured sections; completion is docs that distinguish
  computed readiness truth, owner override, structured question state, and
  markdown fallback. Covers R010-R012, N002-N003.

- [x] T020: Run focused verification for readiness and question services:
  `pytest tests/test_readiness_service.py tests/test_proposal_questions_service.py`;
  completion is reviewed passing output. Covers AC001-AC007, AC010-AC011.

- [x] T021: Run public-surface verification for CLI and MCP:
  `pytest tests/test_cli.py tests/test_mcp.py`; completion is reviewed passing
  output for affected readiness/question tests. Covers AC008-AC009, AC012.

- [x] T022: Run repository validation and the full test suite; completion is
  `p2p validate` or equivalent local validation plus full `pytest` passing
  before implementation is marked complete. Covers AC012.

- [x] T023: Add an implementation note after code changes summarizing design
  choice, compatibility impact, behavior changes, files changed, tests run,
  residual risks, and follow-ups; completion is a local
  `implementation-note.md` under this feature directory with command evidence.
  Covers N008, AC012.
