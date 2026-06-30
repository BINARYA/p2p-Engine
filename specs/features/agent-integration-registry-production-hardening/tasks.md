# Tasks - Agent Integration Registry Production Hardening

- [x] T001: Refresh the existing `agent-integration-registry` spec evidence so
  it references current modules (`services/agent_instructions.py`,
  `services/agent_templates.py`, `cli_commands/agents.py`, MCP catalog/handlers)
  instead of stale pre-refactor line references; completion is updated local
  spec text with no task marked complete without current evidence. Covers AC007.

- [x] T002: Add focused service tests for the mandatory `generic` invariant,
  including effective install sets and service-level refusal to uninstall
  `generic`; completion is failing tests before implementation or passing tests
  after the fix. Covers R001, E001, E002, AC001.

- [x] T003: Enforce `generic` as non-uninstallable in the service path used by
  CLI and MCP; completion is service, CLI, and MCP behavior refusing the
  operation consistently. Covers R001, N001, AC001-AC003.

- [x] T004: Add tests proving CLI init and MCP init use the same default agent
  set when no explicit agent is provided; completion is parity tests covering
  generated files and registry adapters. Covers R002, E003, AC002-AC003.

- [x] T005: Align MCP project initialization default agent semantics with CLI,
  or document and test an explicit exception if deliberately different;
  completion is updated handler/catalog behavior and passing parity tests.
  Covers R002, D005, AC002-AC003.

- [x] T006: Add service tests showing `refresh_agent_instructions` refuses or
  skips drifted/unmanaged existing files by default; completion is coverage for
  drifted `AGENTS.md`, adapter-specific files, and policy file behavior. Covers
  R003, R004, E004, E005, AC001.

- [x] T007: Rework refresh/install/update internals toward a shared conservative
  plan/apply path so drift and unmanaged-file safety is not duplicated or
  bypassed; completion is service code reuse plus existing lifecycle tests still
  passing. Covers R003, R004, N001.

- [x] T008: Replace direct write calls for registry, policy, and generated files
  with atomic write helpers before expanding lifecycle write paths; completion
  is code using shared file helpers and tests or review notes covering temp-file
  behavior. Covers R015, N006.

- [x] T009: Add explicit file status and adapter health calculations in the
  service view layer; completion is tests proving missing, modified, unmanaged,
  and conflicted files do not report adapter health as clean. Covers R005,
  E006-E007, AC001.

- [x] T010: Update `agent list`, `agent show`, and service results to expose
  truthful aggregate health while preserving backward-compatible fields where
  needed; completion is CLI/service tests for clean, warning, and error states.
  Covers R005, N002, AC001-AC002.

- [x] T011: Implement semantic registry validation for mandatory generic,
  known adapters, forbidden active/preferred state, required metadata, relative
  paths, path escape, duplicate path ownership, safe drift/status values, and
  SHA-256 format; completion is validation tests for each invalid condition.
  Covers R006, E001, E008-E014, AC004.

- [x] T012: Extend registry validation to compare existing managed files against
  recorded hashes and report missing files/hash mismatches; completion is tests
  proving `validate` catches real filesystem inconsistency. Covers R007, R008,
  E006-E007, AC004.

- [x] T013: Define shared-file ownership and consumer behavior for adapters that
  only consume shared files, including OpenCode; completion is documented model
  plus tests proving uninstall never removes shared files still referenced by
  another installed adapter. Covers R009, R014, E011-E012, AC001.

- [x] T014: Implement agent doctor service logic that returns structured
  findings for registry validity, file existence, hash mismatch, shared file
  safety, generic baseline, unmanaged targets, and recovery guidance;
  completion is service tests for clean/warning/error health. Covers R010,
  N004, AC001.

- [x] T015: Rework CLI `agent doctor` to render service doctor findings and
  define documented exit behavior for clean/warning/error states; completion is
  CLI tests for output and exit code policy. Covers R011, AC002.

- [x] T016: Expose read-only MCP `p2p_agent_doctor` backed by the same service
  findings as CLI doctor; completion is catalog definition, handler dispatch,
  registry ordering, and structured MCP tests. Covers R012, AC003.

- [x] T017: Make force behavior operation-scoped and explicit in tests for
  update/install/uninstall; completion is non-force tests proving conservative
  behavior and force tests proving only the named operation changes. Covers
  R013, AC001-AC003.

- [x] T018: Add path safety tests for absolute paths, `..`, and project-root
  escape attempts in registry payloads and lifecycle plans; completion is
  validation/service tests proving unsafe paths fail closed. Covers R006, N006,
  E008-E009, AC004.

- [x] T019: Update docs for agent integration registry invariants, safe
  lifecycle behavior, doctor semantics, CLI/MCP parity, force behavior, and
  shared-file policy; completion is docs matching implemented behavior. Covers
  AC006.

- [x] T020: Add an implementation note after code changes summarizing what was
  hardened, what tests ran, and any deferred template/package-data work;
  completion is `implementation-note.md` with command evidence. Covers AC005,
  AC007.

- [x] T021: Add a refinement review after implementation to decide whether
  template package-data relocation, template staleness, dry-run, and JSON CLI
  output should become separate future features; completion is
  `refinement-review.md` with explicit follow-up recommendations.

- [x] T022: Run focused and broad verification after implementation:
  agent service tests, CLI agent tests, MCP agent tests, validation tests, docs
  checks where available, and the full pytest suite; completion is reviewed
  command output recorded in the implementation note. Covers AC001-AC007.
