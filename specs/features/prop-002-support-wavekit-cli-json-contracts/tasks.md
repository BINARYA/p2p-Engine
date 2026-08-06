# Tasks - Support WaveKit CLI JSON Contracts

## Phase 0 - Binding And Inventory

- [x] T001: Bind accepted `PROP-002` to requirements, design and tasks.
  Completion is this feature directory plus the binding report under
  `specs/bindings/`. Covers R001-R007, R050-R055.
- [x] T002: Create a WaveKit CLI contract inventory listing every in-scope
  command, operation id, JSON payload, write/read class, operation-key need,
  receipt behavior, exit behavior and test fixture. Covers R001-R007, AC001.
- [x] T003: Audit current `0.4.9` JSON surfaces for init, project, proposal,
  readiness, questions, contributions, mutation status, verticals, runtime,
  workspace and publish commands. Record gaps without adding broad unrelated
  JSON work. Covers R001-R007, R045-R049.

## Phase 1 - Snapshot Read Model

- [x] T004: Design and implement a bounded project snapshot service/read model
  using existing project, runtime, schema, vertical, readiness, proposal,
  decision, publication and derived-freshness services. Covers R008-R014.
- [x] T005: Add `p2p project snapshot --format json` with `operation:
  project.snapshot` and typed `project_snapshot` data. Covers R008-R014,
  AC002.
- [x] T006: Add snapshot tests for normal project, no proposals, active
  proposals, accepted decisions, selected vertical, stale derived state,
  unsupported schema/pending recovery and truncation metadata. Covers
  R008-R014, AC002.

## Phase 2 - Init Operation Key And Receipt

- [x] T007: Generalize operation-key validation for WaveKit-facing receipt
  writes so `wavekit:<uuid>` is accepted as an opaque bounded key while
  existing receipt callers remain compatible. Covers R016-R021, R046-R047.
- [x] T008: Extend project initialization service result data so it can be
  fingerprinted, receipted and serialized to JSON without relying on human
  output. Covers R015-R024.
- [x] T009: Implement `p2p init --format json --operation-key KEY` with
  durable receipt, exact replay, divergent request conflict and conflict-safe
  behavior for existing workspaces. Covers R015-R024, AC003.
- [x] T010: Add init fault/retry tests for response loss, exact replay,
  divergent replay, unsupported schema, pending transaction recovery and
  non-interactive JSON output. Covers R015-R024, AC003.

## Phase 3 - Proposal Read Contract

- [x] T011: Add typed proposal summary and detail serializers for JSON list/show
  without changing human output. Covers R025-R029.
- [x] T012: Add `p2p proposal list --format json` with filters required by
  WaveKit and deterministic ordering. Covers R025-R026, AC002.
- [x] T013: Add `p2p proposal show PROP --format json` with bounded full detail
  data for Angular proposal screens. Covers R027-R029, AC002.
- [x] T014: Add proposal read tests for empty list, status/decision filters,
  missing proposal, full detail, contribution grouping, readiness and artifact
  state. Covers R025-R029.

## Phase 4 - Proposal Write Contract

- [x] T015: Add receipt-backed proposal create support for
  `p2p proposal create --format json --operation-key KEY`. Covers R030-R032.
- [x] T016: Add receipt-backed proposal update support for
  `p2p proposal update --format json --operation-key KEY`. Covers R033-R034.
- [x] T017: Add create/update tests for success, exact replay,
  divergent-input conflict, missing target, empty update, parser errors and
  response-loss recovery. Covers R030-R034, AC004, AC007.

## Phase 5 - Contribution Contract

- [x] T018: Add JSON output and type filtering for
  `p2p proposal contribution list --format json`, including counts by type and
  bounded/truncated data. Covers R038-R039, AC005.
- [x] T019: Add receipt-backed contribution creation for
  `p2p proposal contribution add --format json --operation-key KEY`. Covers
  R035-R037, R043-R044.
- [x] T020: Decide and implement the contribution review surface: either add a
  governed `proposal contribution review` operation with relevant/rejected
  states, or document review as unsupported in 0.4.10 so WaveKit does not keep
  shadow project-memory status in PostgreSQL. Covers R040-R042, AC006.
- [x] T021: Add contribution tests for suggestion, objection, finding,
  open_question, alternative, invalid type, type filters, exact replay,
  divergent replay, review/rejection if implemented and missing proposal.
  Covers R035-R044, AC005-AC006.

## Phase 6 - Readiness, Questions, Status And Errors

- [x] T022: Verify or add JSON fixtures for proposal readiness and proposal
  question read commands used by WaveKit. Covers R045.
- [x] T023: Extend `p2p mutation status` with `--operation-key` support and
  WaveKit key status classification. Covers R046-R047.
- [x] T024: Normalize WaveKit-facing parser/domain errors and golden fixtures
  for stable codes, exits and sanitized details. Covers R005, R014, R023,
  R029, R034, R048-R049, AC007.

## Phase 7 - MCP, Agent Guidance And Docs

- [x] T025: Update MCP stdio catalog descriptions and parity tests for project,
  proposal and contribution operations without wrapping MCP payloads in
  `p2p-cli/v1`. Covers R050-R052, AC008.
- [x] T026: Update generated agent capability/template guidance so standalone
  agents can discover CLI JSON proposal/contribution operations and understand
  the WaveKit worker boundary. Covers R051-R052, AC008.
- [x] T027: Update `docs/CLI-CONTRACT.md`, `docs/CLI-GUIDE.md`,
  `docs/INSTALL.md`, `README.md` and `CHANGELOG.md` with the implemented
  WaveKit contract and retry/status examples. Covers R050-R055.

## Phase 8 - Release Version Convergence

- [x] T028: Bump implementation references from `0.4.9` to `0.4.10` in
  `pyproject.toml`, `src/p2p_engine/__init__.py`, current release docs and
  version consistency tests only after the behavior is implemented. Covers
  R053-R054, AC009.
- [x] T029: Run and update version consistency tests so stale release URLs,
  package version, MCP server version and current contract docs fail fast.
  Covers R053-R054, AC009.

## Phase 9 - Verification And Handoff

- [x] T030: Run focused tests for CLI contract, mutation receipts,
  initialization, project snapshot, proposals, contributions, readiness,
  questions, MCP catalog and version consistency. Covers AC001-AC009.
- [x] T031: Run public CLI/MCP contract validation and installed-wheel smoke.
  Covers AC001-AC010.
- [x] T032: Run the full test suite and record evidence. Covers AC010.
- [x] T033: Add an implementation note linking completed source, tests, docs,
  fixtures and residual risks back to `PROP-002`. Covers R055, AC010.
