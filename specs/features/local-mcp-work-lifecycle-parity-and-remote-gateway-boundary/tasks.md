# Tasks - Local MCP Work Lifecycle Parity And Remote Gateway Boundary

## Phase 0 - Baseline And Guardrails

- [x] T001: Reconfirm the implementation boundary before coding; completion is
  an implementation note naming the current owner modules
  (`services/work_branches.py`, `services/consent.py`,
  `mcp/catalog/work_specs.py`, `mcp/handlers/work_specs.py`,
  `mcp/consent_audit.py`, `storage/filesystem.py`) and confirming that MCP will
  delegate lifecycle behavior. Covers R001-R038, D001-D012.
  Focused validation: no code required.

- [x] T002: Run a baseline focused test slice for existing Work and MCP
  behavior before edits; completion is recorded passing output or explicit
  residual risk. Covers R001, R037-R038, N005.
  Focused validation: `.venv/bin/pytest tests/test_work_branch_service.py
  tests/test_mcp_work_spec_handler.py tests/test_mcp_registry.py`.

- [x] T003: Inventory existing Work MCP tool names and ensure new names do not
  collide with current catalog/registry entries; completion is a short note in
  implementation summary. Covers R001, R031-R032, AC001.
  Focused validation: `tests/test_mcp_registry.py` after catalog edits.

## Phase 1 - MCP Catalog Contract

- [x] T004: Add MCP catalog definitions for `p2p_work_branch`,
  `p2p_work_submit`, and `p2p_work_review`; completion is registry tests
  proving names, descriptions, required `work_id`, and schema stability. Covers
  R002-R004, R010, R031.
  Focused validation: `.venv/bin/pytest tests/test_mcp_registry.py`.

- [x] T005: Add MCP catalog definitions for `p2p_work_publish`,
  `p2p_work_request_review`, `p2p_work_accept`, `p2p_work_finalize`, and
  `p2p_work_cleanup`; completion is registry tests proving required
  `work_id`, `actor_id`, `consent_id`, and optional operation fields. Covers
  R005-R009, R031, AC001.
  Focused validation: `.venv/bin/pytest tests/test_mcp_registry.py`.

- [x] T006: Add negative registry tests proving no raw Git lifecycle shortcuts
  are exposed, including arbitrary push, merge, reset, clean, force-push,
  checkout, or branch delete tools. Covers R030, AC009.
  Focused validation: `.venv/bin/pytest tests/test_mcp_registry.py`.

## Phase 2 - Preparatory Work MCP Handlers

- [x] T007: Implement `p2p_work_branch` handler dispatch through
  `workspace.branch_work`; completion is focused handler tests for payload
  shape and governance metadata. Covers R002, R010, R018-R020, R032-R034.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py`.

- [x] T008: Implement `p2p_work_submit` handler dispatch through
  `workspace.submit_work`; completion is focused handler tests for payload
  shape and governance metadata. Covers R003, R010, R018-R020, R032-R034.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py`.

- [x] T009: Implement `p2p_work_review` handler dispatch through
  `workspace.review_work`; completion is focused handler tests for payload
  shape and governance metadata. Covers R004, R010, R018-R020, R032-R034.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py`.

- [x] T010: Add public MCP integration tests for preparatory tools only where
  the MCP server path has distinct behavior from direct handler tests;
  completion is either targeted `tests/test_mcp.py` coverage or a documented
  reason that handler plus registry tests are sufficient. Covers N005.
  Public validation: `.venv/bin/pytest tests/test_mcp.py` if integration tests
  are added.

## Phase 3 - Consent/Audit Helper Reuse

- [x] T011: Identify repeated proposal-branch consent/audit logic that should
  be reused for Work handlers; completion is either reuse of existing helpers or
  extraction of neutral helper names without changing proposal MCP behavior.
  Covers R016-R017, D006, N007.
  Focused validation: `.venv/bin/pytest tests/test_mcp.py
  tests/test_mcp_work_spec_handler.py`.

- [x] T012: Add focused tests for the shared consent/audit helper behavior if a
  helper is extracted; completion is tests proving success consumption and
  state-changing failure marking remain compatible. Covers R016-R017.
  Focused validation: helper-specific tests or targeted MCP tests.

- [x] T013: Run proposal-branch MCP regression tests after helper extraction;
  completion is passing existing tests proving proposal publish/review/merge/
  finalize/cleanup behavior did not regress. Covers N001, N007.
  Focused validation: `.venv/bin/pytest tests/test_mcp.py -k "proposal"`.

## Phase 4 - Publish And Request-Review MCP Tools

- [x] T014: Implement `p2p_work_publish` with consent validation for
  `work_publish`; completion is tests proving successful payload, consumed
  consent metadata, branch/remote metadata, and audit behavior. Covers R005,
  R011-R017, R021, R033-R034, AC003-AC004.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py
  tests/test_mcp.py`.

- [x] T015: Add negative tests for `p2p_work_publish` consent errors:
  missing/not granted, operation mismatch, target mismatch, actor mismatch, and
  expired receipt. Covers R011-R015, AC003.
  Focused validation: `.venv/bin/pytest tests/test_mcp.py -k "work_publish"`.

- [x] T016: Add negative tests for `p2p_work_publish` lifecycle errors:
  wrong Work status, wrong current branch, dirty worktree, missing remote, and
  malformed manifest where existing fixtures allow focused coverage. Covers
  R018-R022, N004.
  Focused validation: service tests for domain errors plus one MCP public
  representative if payload/error behavior is distinct.

- [x] T017: Implement `p2p_work_request_review` with consent validation for
  `work_request_review`; completion is tests proving provider advisory metadata
  and no provider PR/MR creation. Covers R006, R011-R017, R021, R029,
  R033-R034, AC004, AC008.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py
  tests/test_mcp.py`.

- [x] T018: Add negative tests for `p2p_work_request_review` consent mismatch
  and invalid provider handling. Covers R011-R015, R029.
  Focused validation: `.venv/bin/pytest tests/test_mcp.py -k "work_request"`.

## Phase 5 - Accept MCP Tool

- [x] T019: Implement `p2p_work_accept` with consent validation for
  `work_accept`; completion is tests proving successful merge payload, consumed
  consent metadata, `merge_performed: true`, and no finalize/cleanup side
  effects. Covers R007, R011-R017, R023-R026, R033-R034, AC004, AC006.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py
  tests/test_mcp.py`.

- [x] T020: Implement structured accept-conflict handling; completion is tests
  proving `work_accept_conflict`, conflicted files, `manual_resolution_required:
  true`, `merge_performed: false`, and consent marked consistently. Covers
  R017, R023, AC005.
  Focused validation: `.venv/bin/pytest tests/test_mcp.py -k "work_accept"`.

- [x] T021: Add negative tests for `p2p_work_accept` wrong base branch, dirty
  worktree, missing managed branch, unpublished branch manifest, malformed
  manifest, and consent mismatch using the lowest useful test layer. Covers
  R011-R015, R018-R022, N004.
  Focused validation: prefer `tests/test_work_branch_service.py` for service
  preconditions and one MCP public error test for consent boundary.

## Phase 6 - Finalize MCP Tool

- [x] T022: Implement `p2p_work_finalize` with consent validation for
  `work_finalize`; completion is tests proving base branch push metadata,
  consumed consent metadata, `finalized: true`, and `cleanup_performed: false`.
  Covers R008, R011-R017, R021, R025-R026, R033-R034, AC004, AC006.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py
  tests/test_mcp.py`.

- [x] T023: Add negative tests for `p2p_work_finalize` wrong status, wrong
  branch, dirty worktree, missing remote, and consent mismatch. Covers
  R011-R015, R018-R022, N004.
  Focused validation: service tests for domain errors plus targeted MCP
  consent/error tests.

## Phase 7 - Cleanup MCP Tool

- [x] T024: Implement `p2p_work_cleanup` with consent validation for
  `work_cleanup`; completion is tests proving local branch deletion metadata,
  consumed consent metadata, and cleanup commit metadata. Covers R009,
  R011-R017, R026-R028, R033-R034, AC004, AC007.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py
  tests/test_mcp.py`.

- [x] T025: Add cleanup tests proving remote branch deletion occurs only when
  `delete_remote` is true and output reports `remote_deleted` accurately.
  Covers R027-R028, AC007.
  Focused validation: `.venv/bin/pytest tests/test_mcp.py -k "work_cleanup"`.

- [x] T026: Add negative tests for cleanup wrong status, wrong branch, dirty
  worktree, missing managed branch, missing remote, and consent mismatch using
  the lowest useful layer. Covers R011-R015, R018-R022, N004.
  Focused validation: service tests for domain errors plus targeted MCP
  consent/error tests.

## Phase 8 - Public MCP Integration And Registry Coverage

- [x] T027: Add MCP integration tests proving all new tools are callable through
  the public MCP server dispatch path and return JSON-ready payloads. Covers
  R031-R034, AC001-AC004.
  Public validation: `.venv/bin/pytest tests/test_mcp.py`.

- [x] T028: Add MCP integration tests proving missing required arguments fail
  through schema/handler validation for representative preparatory and
  consent-gated tools. Covers R031-R032, N003-N004.
  Public validation: `.venv/bin/pytest tests/test_mcp.py`.

- [x] T029: Add MCP registry tests proving tool ordering remains deterministic
  and existing Work read/plan tools retain backward-compatible schemas. Covers
  R001, R031, AC001, AC010.
  Public validation: `.venv/bin/pytest tests/test_mcp_registry.py`.

## Phase 9 - CLI And Service Compatibility

- [x] T030: Run existing Work service tests and update them only if service
  behavior had to change for MCP parity; completion is passing service tests
  and no unnecessary public-layer duplication. Covers R018-R022, R038, N005.
  Focused validation: `.venv/bin/pytest tests/test_work_branch_service.py`.

- [x] T031: Run existing Work CLI tests and update only regressions caused by
  intentional compatible changes; completion is passing targeted CLI tests and
  preserved user-visible CLI behavior. Covers R037, AC010.
  Public validation: `.venv/bin/pytest tests/test_cli.py -k "work_"`.

- [x] T032: Confirm no new raw Git MCP tools were introduced; completion is
  registry assertion and implementation summary note. Covers R030, AC009.
  Public validation: `.venv/bin/pytest tests/test_mcp_registry.py`.

## Phase 10 - Documentation

- [x] T033: Update MCP documentation for new local Work lifecycle tools;
  completion is docs covering tool names, required arguments, consent
  requirements, and high-level response semantics. Covers R031-R036, AC011.
  Focused validation: documentation review plus MCP registry tests.

- [x] T034: Update CLI/developer documentation only where needed to explain
  CLI/MCP parity without changing CLI behavior; completion is docs that keep
  CLI as existing local command surface. Covers R035-R037.
  Focused validation: documentation review.

- [x] T035: Document the remote gateway boundary; completion is explicit text
  saying remote HTTP MCP, Wavekit auth, grants, strong receipts, audit
  retention, tenancy, billing, and rate limits are out of P2P core scope.
  Covers R035-R036, N006, AC011.
  Focused validation: documentation review.

## Phase 11 - Verification

- [x] T036: Run focused handler and registry validation after implementation;
  completion is passing output or explicit residual risk. Covers AC001-AC004.
  Focused validation: `.venv/bin/pytest tests/test_mcp_work_spec_handler.py
  tests/test_mcp_registry.py`.

- [x] T037: Run focused Work service validation; completion is passing output
  proving domain behavior remained compatible. Covers AC010.
  Focused validation: `.venv/bin/pytest tests/test_work_branch_service.py`.

- [x] T038: Run public MCP validation; completion is passing output for the MCP
  public contract. Covers AC001-AC009.
  Public validation: `.venv/bin/pytest tests/test_mcp.py`.

- [x] T039: Run public CLI compatibility validation if CLI code or shared Work
  services were touched; completion is passing output or documented deferral.
  Public validation: `.venv/bin/pytest tests/test_cli.py -k "work_"`.

- [x] T040: Run repository validation and public test subset before commit;
  completion is passing output. Covers AC012.
  Public validation: `.venv/bin/p2p validate` and `./scripts/test-public.sh`.

- [x] T041: Run full suite before commit, push, or merge unless explicitly
  deferred by the owner with residual risk. Covers AC012.
  Full validation: `./scripts/test-full.sh`.

- [x] T042: Add `implementation-note.md` after code changes; completion is a
  concise local note summarizing implemented tools, consent behavior, files
  changed, tests run, compatibility impact, residual risks, and follow-ups.
  Covers N005-N008, AC012.

## Phase 12 - Final Review

- [x] T043: Review implementation against `ENGINEERING_QUALITY_SKILL.md`;
  completion is a checklist confirming no validation bypass, no permission
  bypass, no raw Git shortcuts, no hidden side effects, and no lifecycle logic
  duplication. Covers N001-N008.
  Focused validation: review only unless issues require tests.

- [x] T044: Review tests against `TEST_QUALITY_SKILL.md`; completion is a note
  confirming each new test protects a distinct service, MCP registry, MCP
  payload, consent, error, or documentation contract. Covers N005.
  Focused validation: review only unless redundant tests are removed.

- [x] T045: Prepare final implementation summary; completion is a concise
  summary naming completed requirements, validation commands, unresolved
  risks, and any intentionally deferred remote gateway work. Covers AC012.
  Focused validation: no code required.
