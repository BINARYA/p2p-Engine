# Tasks - MCP Artifact Import Parity

- [x] T001: Review accepted source direction and local implementation boundary;
  completion is a short implementation note or PR summary naming `PROP-088`,
  `CHANGE-066`, `ProposalArtifactService`, `P2PWorkspace`,
  `mcp/catalog/proposals.py`, `mcp/handlers/proposals.py`, MCP registry files,
  docs, and affected tests. Covers N001-N009, D001-D008.

- [x] T002: Add failing public-surface tests for the six new MCP tool names and
  schemas in `tests/test_mcp.py` and/or `tests/test_mcp_registry.py`;
  completion is tests expecting `p2p_explore_import`, `p2p_impact_import`,
  `p2p_clarify_import`, `p2p_synthesize_import`, `p2p_plan_import`, and
  `p2p_tasks_import` with `proposal_id` plus one import input mode. Covers
  R001, AC001.

- [x] T003: Add service tests for source-path parity using existing import
  methods; completion is coverage showing exploration file/directory, impact
  file/directory, clarify, synthesize, plan, and tasks imports still write the
  existing fixed targets. Covers R002-R007, E001-E005, AC002, AC005.

- [x] T004: Add service tests for direct `content` imports; completion is
  coverage proving each supported import kind writes the expected fixed target,
  with tasks YAML and impact YAML validated before write. Covers R008-R010,
  E006-E008, AC003, AC005.

- [x] T005: Add service tests for direct `artifacts` imports; completion is
  exploration and impact multi-file payloads writing only allowlisted filenames
  and validating impact artifact keys. Covers R011-R012, E009-E010, AC004.

- [x] T006: Add service error tests for missing input mode, multiple input
  modes, unsupported filenames, invalid source paths, empty directories,
  single-file tools receiving directory sources, proposal-not-found, invalid
  impact YAML, and invalid tasks YAML. Covers R013-R019, E003, E006-E014,
  AC006.

- [x] T007: Introduce a service-owned import request/result model or small
  helper in `src/p2p_engine/services/proposal_artifacts.py`, or an adjacent
  proposal-artifact import module if extraction is clearer; completion is a
  typed internal boundary for import kind, input mode, imported paths, and
  validation metadata. Covers N001-N003, D004-D006.

- [x] T008: Implement the one-input-mode validation in service-owned code;
  completion is no request can provide none or more than one of `source`,
  `content`, and `artifacts`. Covers R013-R014, D003.

- [x] T009: Implement payload-mode import for exploration artifacts; completion
  is `content` writing `exploration.md`, `artifacts` accepting only the
  exploration allowlist, and source-path behavior unchanged. Covers R002, R008,
  R011, R016, D002-D004.

- [x] T010: Implement payload-mode import for impact artifacts; completion is
  `content` writing validated `impact-map.yml`, `artifacts` accepting only
  known impact filenames, and each YAML file requiring the correct top-level
  key. Covers R003, R009, R012, R016, D002-D004.

- [x] T011: Implement payload-mode import for generated single-target
  artifacts; completion is `clarify`, `synthesize`, `plan`, and `tasks`
  payload imports writing `clarifications.md`, `proposal.md`,
  `execution-plan.md`, and validated `tasks.yml`. Covers R004-R007, R010,
  D002-D004.

- [x] T012: Add `P2PWorkspace` facade delegation for the new import behavior
  only if the MCP handler needs it; completion is a thin method that delegates
  to the proposal artifact service and adds no domain logic to
  `src/p2p_engine/storage/filesystem.py`. Covers N002, D005.

- [x] T013: Add MCP catalog definitions in
  `src/p2p_engine/mcp/catalog/proposals.py`; completion is explicit write-safe
  descriptions and schemas for all six import tools, including the supported
  input modes and no decision authority. Covers R001, R020, R023, AC001.

- [x] T014: Register the new MCP tool names in `src/p2p_engine/mcp/registry.py`;
  completion is registry completeness checks passing with no duplicate or
  unexpected tool definitions. Covers R001, N005, AC001.

- [x] T015: Implement MCP handler dispatch in
  `src/p2p_engine/mcp/handlers/proposals.py`; completion is each import tool
  parsing arguments, delegating to workspace/service behavior, returning
  `artifact_import` metadata and governance metadata, and keeping the handler
  free of target-file write logic. Covers R018, R020-R023, N001-N003, D006-D008.

- [x] T016: Add MCP handler tests for source-path imports; completion is
  `handle_proposal_tool` and/or `call_tool` proving each tool writes the same
  target files as CLI-backed imports and returns structured metadata. Covers
  R002-R007, R018, AC002.

- [x] T017: Add MCP handler tests for direct `content` imports; completion is
  MCP-level proof that clients can import generated content without creating a
  caller-managed source file. Covers R008-R010, R018, AC003.

- [x] T018: Add MCP handler tests for direct `artifacts` imports and rejected
  filenames; completion is MCP-level proof of exploration and impact allowlists
  plus validation failures. Covers R011-R015, AC004, AC006.

- [x] T019: Add MCP error tests for invalid requests; completion is public
  behavior proving missing input, multiple input modes, invalid source,
  proposal-not-found, invalid impact YAML, and invalid tasks YAML fail without
  uncontrolled writes. Covers R013-R019, R023, AC006.

- [x] T020: Preserve prompt-tool behavior; completion is existing or updated
  regression tests proving `p2p_explore_prompt`, `p2p_impact_prompt`,
  `p2p_clarify_prompt`, `p2p_synthesize_prompt`, `p2p_plan_prompt`, and
  `p2p_tasks_prompt` generate prompts only and do not import outputs. Covers
  R022, AC007.

- [x] T021: Update MCP documentation in `docs/MCP.md`; completion is docs
  covering tool names, input modes, supported artifact kinds, examples for
  `source` and `content`, unsupported generic import, validation errors, and
  the distinction between content import and artifact coverage state. Covers
  AC008.

- [x] T022: Update adjacent user or agent docs only if implementation exposes
  behavior there; completion is either a focused docs change or an explicit
  implementation note that `docs/MCP.md` is the only required public docs
  surface. Covers AC008.

- [x] T023: Run focused service validation:
  `.venv/bin/pytest tests/test_proposal_artifact_service.py`; completion is
  reviewed passing output. Covers AC002-AC006.

- [x] T024: Run focused MCP validation:
  `.venv/bin/pytest tests/test_mcp_proposal_handler.py tests/test_mcp_registry.py`;
  completion is reviewed passing output. Covers AC001-AC007.

- [x] T025: Run public-contract MCP validation:
  `.venv/bin/pytest tests/test_mcp.py`; completion is reviewed passing output
  for tool listing, `call_tool`, prompt regression, and JSON-RPC behavior.
  Covers AC001-AC007.

- [x] T026: Run repository validation and full test suite before handoff:
  `.venv/bin/p2p validate` and `.venv/bin/pytest`; completion is passing output
  or an explicit residual-risk note if the owner defers full validation. Covers
  AC009.

- [x] T027: Add `implementation-note.md` after code changes; completion is a
  local summary under this feature directory with design choice, compatibility
  impact, behavior changes, files changed, tests run, residual risks, and
  follow-ups. Covers N006, AC009.
