# Tasks - Proposal Readiness Review And Questions

- [x] T001: Review existing readiness, proposal document, agent template, MCP,
  validation, and registry service boundaries; completion is a short
  implementation note confirming no new domain logic belongs directly in
  `cli.py`, `storage/filesystem.py`, or `mcp/tools.py`. Covers R001-R020.

- [x] T002: Add core question dataclasses/enums in
  `src/p2p_engine/core/proposal_questions.py`; completion is typed records for
  states, priorities, question items, groups, list/status results, and operation
  results. Covers R003-R009.

- [x] T003: Add `ProposalQuestionService` with read, validate, write, init,
  status, list, add, answer, defer, mute, reopen, group-state, next, reassess,
  apply-summary, and import operations; completion is focused service tests for
  normal and error paths. Covers R001-R012, N002-N004, E001-E007.

- [x] T004: Add `P2PWorkspace` facade delegation for question operations;
  completion is existing public workspace behavior preserved and service tests
  using the facade where useful. Covers N005.

- [x] T005: Add `p2p proposal questions ...` CLI command module and register it
  under proposal commands; completion is CLI tests for init/status/list/add/
  answer/defer/mute/reopen/group-status/next/reassess/apply/import. Covers
  R001-R012 and AC001-AC003.

- [x] T006: Extend validation to inspect present question state files while
  treating absent files as valid; completion is validation tests for missing,
  valid, and malformed question state. Covers R001, N003, E001, E003, AC008.

- [x] T007: Improve `proposal readiness refresh` output so conservative refresh
  reports when review/interview is needed and names next commands; completion is
  CLI tests proving existing refresh behavior remains compatible and guidance is
  additive. Covers R014, N001, AC004.

- [x] T008: Add readiness `review` or `assess` behavior that reads proposal
  artifacts, contributions, readiness, and question state to produce evidence,
  missing items, owner questions, challenge points, acceptance cautions, and
  next actions; completion is service and CLI tests for weak, answered, and
  missing-question-state proposals. Covers R010-R016, AC006.

- [x] T009: Update generated agent instructions and local/project skills to
  include proactive proposal interview behavior, one-question-at-a-time flow,
  defer/muted handling, answer application, and owner-governance boundaries;
  completion is snapshot or content tests for generated instructions. Covers
  R019, AC005.

- [x] T010: Add advisory duplicate/aggregation candidate reporting to readiness
  review using existing proposal summaries/contributions where feasible;
  completion is tests proving candidates are reported without changing proposal
  decisions. Covers R017-R018, E008, AC007.

- [x] T011: Add MCP catalog and handler coverage for question read/write tools
  and readiness review if MCP parity is in scope for the implementation slice;
  completion is MCP tests proving schemas describe read/write behavior and
  governance remains owner-controlled. Covers R020.

- [x] T012: Update docs for public CLI behavior once implemented; completion is
  docs that describe question lifecycle, refresh vs review, proactivity, and
  backward compatibility. Covers N001 and public behavior.

- [x] T013: Run focused validation and tests:
  `.venv/bin/pytest tests/test_readiness_service.py`,
  question service tests, CLI tests, MCP tests if touched, `.venv/bin/p2p
  validate`; completion is reviewed passing output or documented failures.
  Covers AC009.

## Second Slice - Artifact-Aware Apply And Evidence-Aware Reassessment

- [x] T014: Extend question apply results with an artifact-aware update plan;
  completion is service and CLI tests proving answered questions name affected
  artifacts/actions/statuses before being marked applied. Covers R021-R022,
  AC010.

- [x] T015: Add evidence-aware `proposal readiness assess`; completion is a
  service/CLI path that recalculates from current artifacts, question state, and
  owner-question state while keeping `refresh` conservative. Covers R023,
  AC011.

- [x] T016: Add stepped assertiveness guidance to readiness review/assess and
  generated agent instructions; completion is tests for weak, partial, strong,
  and decision-ready guidance text. Covers R024-R025, AC012.

- [x] T017: Add advisory duplicate/aggregation candidate reporting to readiness
  review using existing proposal summaries where feasible; completion is tests
  proving candidates are reported without changing proposal decisions. Covers
  R017-R018, E008, AC007.

- [x] T018: Add MCP coverage for readiness assess and enriched question apply if
  public MCP parity is maintained in this slice; completion is MCP registry and
  handler tests. Covers R020-R023.

- [x] T019: Update docs and implementation note for second-slice behavior;
  completion is CLI/MCP docs plus local implementation note.

- [x] T020: Run full validation and tests; completion is passing `.venv/bin/p2p
  validate` and pytest output.
