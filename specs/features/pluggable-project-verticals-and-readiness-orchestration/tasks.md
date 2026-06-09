# Tasks - Pluggable Project Verticals And Readiness Orchestration

- [x] T001: Review existing project initialization, project rubrics/maturity,
  visible export, validation, agent template, CLI project commands, MCP project
  tools, and `P2PWorkspace` facade boundaries; completion is a short
  implementation note confirming where vertical behavior will live and that no
  domain logic is added directly to `cli.py`, `storage/filesystem.py`, or
  `mcp/tools.py`. Covers R001-R038, N001-N002.

- [x] T002: Add core project vertical models in
  `src/p2p_engine/core/project_verticals.py`; completion is typed records for
  vertical packs, sections, rubrics, questions, artifacts, profiles, modules,
  source metadata, active state, validation issues, custom candidates, proposal
  coverage, and review summaries. Covers R001-R007, R024-R033.

- [x] T003: Add internal resource layout for `base_project`; completion is a
  package resource pack containing the required cross-domain sections, minimal
  rubrics, blocking questions, and expected artifacts. Covers R008-R010, AC001.

- [x] T004: Add one complete demonstration vertical resource; completion is a
  valid internal pack that extends `base_project`, has section/rubric/question/
  artifact coverage, and is useful for end-to-end tests. Covers R010, AC001,
  AC013.

- [x] T005: Add `ProjectVerticalService` loader and source precedence behavior;
  completion is service tests proving project-local packs override internal
  defaults, missing active state falls back to `base_project`, and unknown IDs
  produce actionable diagnostics. Covers R010-R013, R017-R020, N003, E001-E003,
  AC001-AC006.

- [x] T006: Add vertical pack schema validation; completion is validation tests
  for required metadata, duplicate IDs, section links, rubric links, question
  links, artifact links, optional fields, and extra files. Covers R001-R007,
  R016, N005, E003-E006, AC003.

- [x] T007: Add project-local vertical persistence and active vertical state;
  completion is atomic-write service tests for add/select behavior and no active
  state mutation when add fails. Covers R013, R016-R017, R022-R023, N004,
  AC002, AC005.

- [x] T008: Add custom vertical candidate generation; completion is service and
  CLI tests proving `project vertical propose` returns an importable candidate
  with id/name, sections, rubrics, questions, artifacts, and base-project
  rationale without persisting or activating it. Covers R014-R015, R021, AC004.

- [x] T009: Add `p2p project vertical ...` CLI command module and registration;
  completion is CLI tests for list/show/validate/propose/add/select and
  user-facing output for source, active status, and validation errors. Covers
  R018-R023, E002-E006, AC004-AC005.

- [x] T010: Add `P2PWorkspace` facade delegation for project vertical operations;
  completion is public facade methods with tests or CLI coverage proving service
  delegation and compatibility. Covers N001-N002.

- [x] T011: Add proposal vertical coverage model and storage/import behavior;
  completion is tests proving coverage can declare proposal ID, vertical ID,
  section IDs, relevance, rationale, and source, and invalid section IDs are
  reported. Covers R029-R030, E007, AC008.

- [x] T012: Add validation coverage for project-local vertical packs, active
  vertical state, and proposal vertical coverage artifacts; completion is
  validation tests for missing, valid, malformed, and unknown-section cases.
  Covers R016, R029-R030, N005, E004-E007, AC003, AC008.

- [x] T013: Add project readiness review service; completion is service tests
  proving it reads project context, rubrics/maturity, active/fallback vertical,
  proposals, decisions, and coverage evidence. Covers R024-R028, AC006-AC007.

- [x] T014: Add vertical skeleton coverage computation; completion is tests for
  covered, partial, missing, and not-applicable section statuses, including a
  project with no proposals. Covers R025-R027, R031-R033, E008, AC007-AC009.

- [x] T015: Add unmapped proposal detection in project readiness review;
  completion is tests proving proposals affecting the project but lacking
  vertical coverage are listed without changing governance state. Covers R032-
  R033, N009, AC009.

- [x] T016: Add `p2p project readiness review` CLI command; completion is CLI
  tests proving fallback, active vertical, section coverage, generated
  questions, unmapped proposals, and suggested next commands render correctly.
  Covers R024-R028, R031-R033, E008-E009, AC007-AC009.

- [x] T017: Integrate vertical-derived criteria with existing project
  rubrics/maturity without replacing current behavior; completion is tests
  proving existing rubrics still work and vertical review can use vertical
  rubrics as evidence/input. Covers R028, R036, N006, AC006, AC014.

- [x] T018: Update project initialization behavior only where deterministic;
  completion is tests proving `p2p init` remains scriptable/non-agentic and
  missing vertical state is normal. Covers R012, R034, R036, N006, AC006,
  AC014.

- [x] T019: Update generated agent/project instructions with project
  orchestrator guidance; completion is content tests proving instructions cover
  missing initialization, capisaldi, active vertical, custom candidate propose/
  add/select flow, project readiness review, and owner governance boundaries.
  Covers R034-R035, N010, AC010.

- [x] T020: Add MCP catalog, handler, registry, and tests for project vertical
  operations and project readiness review; completion is MCP tests proving
  schemas state read/write behavior and handlers delegate to workspace facade
  without governance decisions. Covers R038, AC011.

- [x] T021: Update visible project export to include vertical skeleton coverage
  summary when available; completion is tests proving exports remain compatible
  when no vertical state exists and include coverage when review data exists.
  Covers R031-R033, AC009, AC014.

- [x] T022: Update public docs for vertical packs and review workflow;
  completion is docs describing pack layout, `base_project`, custom candidates,
  CLI commands, source precedence, proposal coverage, project readiness review,
  and registry deferral. Covers AC012.

- [x] T023: Add package resource build verification; completion is a focused
  test or build check proving internal vertical resources are included in the
  wheel/installable package. Covers N008, AC013.

- [x] T024: Add regression tests for existing project init, rubrics, maturity,
  proposal readiness, proposal questions, visible export, MCP registry, and
  validation behavior; completion is reviewed passing output or documented
  failures with no unrelated behavior changes. Covers R036, AC014.

- [x] T025: Run focused validation and full tests; completion is passing
  `.venv/bin/p2p validate` and relevant pytest targets, then full
  `.venv/bin/pytest` if runtime code or public CLI/MCP surfaces changed. Covers
  AC015.

- [x] T026: Prepare implementation note after coding; completion is a local note
  summarizing implemented slices, deferred registry/plugin work, verification
  output, and any intentional deviations from these specs.
