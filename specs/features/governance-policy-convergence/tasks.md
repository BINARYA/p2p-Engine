# Tasks - Governance Policy Convergence

## Phase 0 - Baseline And Guardrails

- [x] T001: Reconfirm the implementation boundary before coding; completion is
  a short working note or implementation summary naming the current owner
  modules (`services/governance.py`, `services/choices.py`,
  `services/permissions.py`, `services/validation.py`, `storage/filesystem.py`,
  CLI governance/choice commands, MCP catalog/handlers) and confirming that new
  preflight classification logic will stay in a service. Covers N001-N008,
  D001-D002.
  Focused validation: no code required; if code is touched, run the affected
  focused tests.

- [x] T002: Inventory existing governance, vote, precedent, and choice public
  behavior; completion is a checklist in the implementation summary of current
  CLI commands, MCP tools, service methods, persisted files, and tests that must
  remain compatible. Covers R022-R026, R032-R034, N002.
  Focused validation: `.venv/bin/pytest tests/test_governance_service.py
  tests/test_choice_lifecycle_service.py`.

- [x] T003: Add regression tests proving current governance status, vote
  status, vote record, precedent record, and choice decision behavior remains
  unchanged before adding new preflight behavior. Covers R026, R033-R034, N002.
  Focused validation: `.venv/bin/pytest tests/test_governance_service.py
  tests/test_choice_lifecycle_service.py`.

## Phase 1 - Preflight Models And Serialization

- [x] T004: Add typed preflight/domain result models for target, governance
  context, actor, selection, result, diagnostics, vote summary, blockers, and
  precedents; completion is model tests proving deterministic serialization and
  `schema_version: governance-preflight/v1`. Covers R001-R002, R035, D003.
  Focused validation: new service/model test file only.

- [x] T005: Add stable diagnostic code constants or enums for governance
  warnings and blocking errors; completion is tests proving codes are emitted in
  structured diagnostics rather than only human text. Covers R011-R016,
  R020-R021, N004, D004.
  Focused validation: new service/model test file only.

- [x] T006: Add a read-only filesystem write-guard fixture or helper for
  governance tests; completion is reusable focused tests that can detect writes
  from preflight/status/validate/search operations without relying on local
  machine state. Covers R003, N003, AC009.
  Focused validation: helper tests or first service no-write test.

## Phase 2 - Actor And Governance Context Resolution

- [x] T007: Implement governance context loading with default
  `owner_decides`; completion is service tests for configured mode, missing
  governance file fallback, unsupported mode blocking error, and no writes.
  Covers R004, R015-R016, R034, D001, D004.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

- [x] T008: Implement permissions-first actor resolution; completion is service
  tests for owner, maintainer/contributor, unknown actor, malformed
  `permissions.yml`, and no writes. Covers R008, R011-R012, R015, D005.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_permissions_consent_services.py`.

- [x] T009: Implement legacy governance-role fallback only when
  `permissions.yml` is absent; completion is service tests proving fallback
  evidence and warning are returned. Covers R009, R016, R034, D005.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

- [x] T010: Implement role mismatch detection between `permissions.yml` and
  legacy governance roles; completion is service tests proving a warning is
  emitted and `permissions.yml` remains authoritative. Covers R010, R016, D005.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

## Phase 3 - Vote Evidence And Selection Classification

- [x] T011: Implement selected-option resolution for choice preflight;
  completion is service tests for option id, option title, existing selected
  option, missing selection, and invalid selection diagnostics. Covers R001,
  R015, D003.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_choice_lifecycle_service.py`.

- [x] T012: Implement advisory vote summary inside preflight; completion is
  service tests for no votes, single winner, tie, malformed votes, and stable
  sorted counts. Covers R005, R007, R015-R016, R035, D006.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_governance_service.py`.

- [x] T013: Implement vote alignment classification; completion is service
  tests proving aligned, conflict, tied, no-votes, and not-applicable states,
  with vote conflict/tie reported as warnings only. Covers R005-R007, D006,
  AC002.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

## Phase 4 - Blockers And Result Semantics

- [x] T014: Implement active explicit blocker collection for choice targets;
  completion is service tests for active blockers, inactive blockers, malformed
  `links.yml`, sorted blocker output, and no writes. Covers R013, R015, R035,
  D007.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_choice_lifecycle_service.py`.

- [x] T015: Implement result status classification; completion is service tests
  for ready/blocked/owner-override outcomes, including owner
  override rationale signaling for active explicit blockers. Covers R013-R016,
  D007, AC004.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

- [x] T016: Prove non-owner actors cannot pass owner-controlled finalization;
  completion is service tests for contributor/agent actors receiving blocking
  diagnostics even when votes align. Covers R011-R012, R015, AC003.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

## Phase 5 - Deterministic Precedent Search

- [x] T017: Add precedent payload parsing and validation helpers; completion is
  tests for valid precedents, duplicate ids, malformed records, missing optional
  file, and stable sorted output. Covers R017-R021, R034-R035, D008-D009.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

- [x] T018: Implement deterministic precedent search by explicit precedent id,
  related proposal id, related choice id, and declared tag; completion is tests
  proving each match reason and source path is reported. Covers R017-R019,
  D008, AC005.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

- [x] T019: Add negative tests proving title-only, fuzzy, semantic, and
  unrelated text similarity do not create precedent matches. Covers R018, D008,
  AC005.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

- [x] T020: Wire precedent matches into choice governance preflight; completion
  is service tests proving preflight includes explicit precedent evidence and
  remains deterministic. Covers R001, R019, R035.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

## Phase 6 - Validation Integration

- [x] T021: Extend repository validation for governance policy artifacts;
  completion is validation tests for invalid governance mode, malformed roles,
  duplicate precedent ids, malformed precedent records, malformed votes, and
  invalid vote choices. Covers R020-R021, D009, AC006.
  Focused validation: `.venv/bin/pytest tests/test_validation_service.py`.

- [x] T022: Prove missing optional governance artifacts remain compatible;
  completion is validation tests showing absent optional governance/vote/
  precedent files do not fail validation by themselves. Covers R034, D009.
  Focused validation: `.venv/bin/pytest tests/test_validation_service.py`.

- [x] T023: Add governance-only validation service/facade method; completion is
  a read-only method returning only governance diagnostics without running
  unrelated repository validation domains. Covers R003, R020-R023, R033.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_validation_service.py`.

## Phase 7 - Workspace Facade

- [x] T024: Add thin `P2PWorkspace` delegation for governance policy service
  methods; completion is facade tests or existing service tests proving the
  facade calls service-owned behavior without duplicating classification logic.
  Covers R033, N001.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py`.

- [x] T025: Confirm `P2PWorkspace` does not gain unrelated domain logic;
  completion is implementation summary evidence listing only constructor wiring
  and delegating facade methods in `storage/filesystem.py`. Covers N001, N008,
  D001.
  Focused validation: covered by T024.

## Phase 8 - CLI Public Surfaces

- [x] T026: Add `p2p governance validate`; completion is CLI tests for text
  output, exit behavior, no-write behavior, and at least one invalid governance
  artifact diagnostic. Covers R003, R023, R026, AC007, AC009.
  Public validation: targeted CLI governance tests.

- [x] T027: Preserve `p2p governance status` default text and add machine output
  only if needed; completion is CLI tests proving existing text remains stable
  and JSON/YAML output is parseable if introduced. Covers R022, R025-R026.
  Public validation: targeted CLI governance tests.

- [x] T028: Add `p2p choice governance-preflight CHOICE-XXX --option <option>
  --actor <actor>`; completion is CLI tests for ready, warning, blocked,
  parseable machine output, and no choice decision write. Covers R003,
  R024-R026, AC007, AC009.
  Public validation: targeted CLI choice/governance tests.

- [x] T029: Add or extend `p2p vote status` machine output; completion is CLI
  tests proving existing default text remains compatible and JSON/YAML is
  parseable where supported. Covers R005, R025-R026.
  Public validation: targeted CLI governance/vote tests.

- [x] T030: Add `p2p precedent search`; completion is CLI tests for explicit id,
  related proposal, related choice, tag, no matches, parseable machine output,
  and no writes. Covers R017-R019, R025-R026, AC007, AC009.
  Public validation: targeted CLI precedent tests.

## Phase 9 - MCP Read-Only Phase One

- [x] T031: Add MCP catalog definitions for `p2p_governance_status`,
  `p2p_governance_validate`, `p2p_choice_governance_preflight`,
  `p2p_vote_status`, and `p2p_precedent_search`; completion is registry tests
  proving names, strict schemas, required fields, and ordering. Covers
  R027-R031, D011, AC008.
  Public validation: `.venv/bin/pytest tests/test_mcp_registry.py`.

- [x] T032: Add MCP handler dispatch for the five read-only governance tools;
  completion is MCP tests proving payload shape, no mutation, and
  `mutation_performed: false` or equivalent evidence where included. Covers
  R027-R031, D011, AC008-AC009.
  Public validation: `.venv/bin/pytest tests/test_mcp.py`.

- [x] T033: Add negative MCP contract tests proving this phase does not expose
  `vote_record`, `precedent_record`, or `choice_decide` write tools through the
  new governance policy MCP surface. Covers R032, D011.
  Public validation: `.venv/bin/pytest tests/test_mcp_registry.py tests/test_mcp.py`.

## Phase 10 - Documentation And Agent Guidance

- [x] T034: Update developer or command documentation for governance preflight;
  completion is docs that distinguish owner final decision, advisory vote
  warnings, active blocker handling, deterministic precedents, and read-only
  preflight from actual choice decision. Covers R004-R019, R022-R032.
  Focused validation: documentation review plus relevant CLI tests if examples
  are executable.

- [x] T035: Add agent-facing guidance for future governance tests; completion is
  a short note in docs or implementation summary explaining lowest-useful-layer
  coverage, when CLI/MCP tests are justified, and why fuzzy precedent tests stay
  outside core. Covers N006, AC010.
  Focused validation: no code required.

## Phase 11 - Verification

- [x] T036: Run focused service validation:
  `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_governance_service.py tests/test_choice_lifecycle_service.py
  tests/test_permissions_consent_services.py`; completion is reviewed passing
  output or explicit residual risk. Covers AC001-AC005, AC009.

- [x] T037: Run validation-focused tests:
  `.venv/bin/pytest tests/test_validation_service.py`; completion is reviewed
  passing output. Covers AC006.

- [x] T038: Run public CLI/MCP validation:
  `.venv/bin/pytest tests/test_mcp_registry.py tests/test_mcp.py` plus the
  targeted CLI test file(s) touched by the implementation; completion is
  reviewed passing output. Covers AC007-AC008.

- [x] T039: Run repository validation and full test suite before marking the
  feature complete: `.venv/bin/p2p validate` or equivalent read-only
  validation, then `./scripts/test-full.sh` or `.venv/bin/pytest`; completion is
  passing output or an explicitly documented owner-approved deferral. Covers
  AC010.

- [x] T040: Add `implementation-note.md` after code changes; completion is a
  local note summarizing design choice, compatibility impact, behavior changes,
  files changed, tests run, residual risks, and follow-ups. Covers N007-N008,
  AC010.

## Phase 12 - Contract Refinement Before Commit

Scope note: this phase intentionally covers the agreed refinements for
`result.status`, malformed precedent handling, vote alignment naming, related
precedent warnings, and malformed present `governance.yml`. It intentionally
does not address blocker direction semantics or `requires_rationale` policy for
vote conflicts/precedents; those require separate exploration.

- [x] T041: Align `governance-preflight/v1` result statuses to the accepted
  contract; completion is service tests and CLI/MCP payload tests proving
  `ready`, `requires_owner_override`, and `blocked` replace `ok`,
  `override_required`, and `invalid`, while blocking details remain in
  `blocking_errors`. Covers R036, D003, D007.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_cli.py::test_cli_governance_policy_read_only_surfaces
  tests/test_mcp.py::test_mcp_governance_policy_read_only_tools`.

- [x] T042: Normalize advisory vote conflict alignment to `conflicts`;
  completion is service, CLI, MCP, and docs/tests updated so the stable payload
  uses `vote_summary.alignment: conflicts` and no tests assert the singular
  `conflict`. Covers R006, D006.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_cli.py::test_cli_governance_policy_read_only_surfaces
  tests/test_mcp.py::test_mcp_governance_policy_read_only_tools`.

- [x] T043: Convert malformed `decision-precedents.yml` during preflight into a
  structured blocking diagnostic; completion is tests proving
  `P2P_GOV_MALFORMED_PRECEDENTS`, empty `precedents`, `result.status:
  blocked`, and no uncaught exception from CLI/MCP preflight. Covers R021A,
  AC006A, D008.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_cli.py::test_cli_governance_policy_read_only_surfaces
  tests/test_mcp.py::test_mcp_governance_policy_read_only_tools`.

- [x] T044: Implement malformed present `governance.yml` as fail-closed
  preflight behavior; completion is tests proving missing `governance.yml`
  still defaults to `owner_decides`, while present non-mapping `governance`
  returns `P2P_GOV_MALFORMED_GOVERNANCE`, `governance.mode: invalid`, and
  `result.status: blocked`. Covers R021A, AC006A, D012.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_validation_service.py`.

- [x] T045: Add related-precedent warnings to preflight; completion is service,
  CLI, and MCP tests proving deterministic precedent matches remain listed in
  `precedents` and also emit `P2P_GOV_RELATED_PRECEDENTS` warning without
  becoming blocking errors. Covers R019A, AC005A, D008.
  Focused validation: `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_cli.py::test_cli_precedent_search_matches_explicit_fields_only
  tests/test_mcp.py::test_mcp_governance_policy_read_only_tools`.

- [x] T046: Update CLI/MCP/docs examples after status/alignment refinements;
  completion is `docs/CLI-GUIDE.md`, `docs/MCP.md`, and
  `implementation-note.md` reflecting `ready`, `requires_owner_override`,
  `blocked`, `conflicts`, and `P2P_GOV_RELATED_PRECEDENTS`. Covers R025,
  R027-R031, AC007-AC008.
  Public validation: `.venv/bin/pytest tests/test_cli.py tests/test_mcp.py
  tests/test_mcp_registry.py`.

- [x] T047: Run focused, public, validation, and full verification after the
  refinement; completion is reviewed passing output for
  `.venv/bin/pytest tests/test_governance_policy_service.py
  tests/test_validation_service.py tests/test_cli.py tests/test_mcp.py
  tests/test_mcp_registry.py`, `.venv/bin/p2p validate`, and
  `.venv/bin/pytest`. Covers AC001-AC010 plus AC005A and AC006A.
