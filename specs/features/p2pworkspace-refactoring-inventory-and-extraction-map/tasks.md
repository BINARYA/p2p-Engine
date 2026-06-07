# P2PWorkspace Refactoring Inventory And Extraction Map Tasks

## Tasks

### Phase 1 - Inventory Document Setup

- [x] T001: Create
  `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/inventory.md`;
  completion is a document skeleton with sections for file inventory, method
  map, responsibility groups, target modules, test map, extraction order,
  facade contract, and follow-up features.

- [x] T002: Record source measurement baseline for R001; completion is
  `inventory.md` listing line counts for `filesystem.py`, `cli.py`,
  `mcp/tools.py`, `storage/git.py`, `core/`, `exporters/`, `prompts/`,
  `tests/test_cli.py`, and `tests/test_mcp.py`.

- [x] T003: Record current file responsibility matrix for R001; completion is a
  table mapping each source/test file to current responsibility, refactoring
  concern, and whether it is facade, domain, adapter, presentation, tests, or
  helper code.

- [x] T004: Record generated/non-source context for R001; completion is a note
  distinguishing source code from `.p2p` state, docs, and local `specs/`, so
  refactoring tasks do not treat generated state as runtime implementation.

### Phase 2 - P2PWorkspace Method Map

- [x] T005: Extract the full `P2PWorkspace` method list for R002; completion is
  a sorted list of public methods and significant private helpers with source
  line references.

- [x] T006: Map initialization and agent methods for R002; completion assigns
  init, domain/rubrics setup, agent instruction generation, agent registry, and
  adapter file methods to target groups and candidate modules.

- [x] T007: Map permissions and consent methods for R002; completion assigns
  permission policy, actors, consent grant/request/show/status/revoke/validate/
  consume/error, payload normalization, paths, and receipt parsing to target
  groups and candidate modules.

- [x] T008: Map remote, sync, and Git-related methods for R002; completion
  assigns remote profile, sync status/fetch/pull/push, branch metadata,
  merge/finalize/cleanup helpers, and Git helper calls to target groups and
  candidate modules.

- [x] T009: Map proposal lifecycle methods for R002; completion assigns
  proposal list/show/create/update/contribution/decision/branch/publish/review/
  merge/finalize/cleanup/scan behavior to target groups and candidate modules.

- [x] T010: Map readiness, context, assessment, and maturity methods for R002;
  completion assigns readiness profile/read/write/refresh/init/override,
  context packets, project assessment, rubrics, and maturity computation to
  target groups and candidate modules.

- [x] T011: Map prompt and import methods for R002; completion assigns explore,
  digest, clarify, synthesize, plan, tasks, impact, project brief, intake, and
  software spec prompt/import behavior to target groups and candidate modules.

- [x] T012: Map project state, registries, validation, and parsing helpers for
  R002; completion assigns project refresh/show/status, registries,
  validation, YAML/Markdown/frontmatter parsing, ID discovery, slugging, and
  artifact quality helpers to target groups and candidate modules.

- [x] T013: Map Change Set, Work, choices, conflicts, and next actions for
  R002; completion assigns change lifecycle, work planning/branch/submit/
  review/publish/accept/finalize/cleanup, choices, blockers, conflicts, impact,
  and next-action behavior to target groups and candidate modules.

- [x] T014: Map software-spec and export methods for R002; completion assigns
  spec refresh/status/show/prompt/import/export/validate, project definition,
  generic/OpenSpec/Spec Kit renderers, and export helper functions to target
  groups and candidate modules.

### Phase 3 - Target Module Boundaries

- [x] T015: Define candidate service boundary template for R003; completion is
  a template with service name, owns, does not own, inputs, outputs, storage
  paths, side effects, facade methods, tests, and extraction risk.

- [x] T016: Define permissions/consent target boundary for R003; completion is
  a detailed proposed module split and facade relationship for the first future
  extraction.

- [x] T017: Define proposal/readiness target boundaries for R003; completion is
  recommended modules and boundaries for proposal lifecycle and readiness
  review without starting implementation.

- [x] T018: Define project state/registry/spec-export boundaries for R003;
  completion is recommended modules and boundaries for generated project state,
  registries, software-spec, and project definition export.

- [x] T019: Define work/sync/Git boundaries for R003; completion is recommended
  modules and boundaries for managed work, proposal branches, sync, Git command
  wrappers, and richer Git error handling.

- [x] T020: Define CLI and MCP target boundaries for R003; completion is a
  recommendation for when to introduce `cli_commands/*` and MCP tool registry
  modules after services exist.

### Phase 4 - Compatibility Test Map

- [x] T021: Map CLI tests for permissions/consent for R004; completion links
  current tests covering permission actors, consent receipts, owner approver
  validation, and invalid permission policy validation.

- [x] T022: Map MCP tests for permissions/consent for R004; completion links
  current tests covering permission/consent read tools, consent request,
  permission-gated operations, consent consumption, mismatch handling, and
  audit behavior.

- [x] T023: Map CLI tests for proposal/readiness/governance for R004;
  completion links current tests covering proposal creation/update/show/list,
  decisions, contributions, readiness, prompts, and governance actions.

- [x] T024: Map CLI/MCP tests for project state, registries, spec/export, and
  work for R004; completion links current tests for project refresh,
  registries, spec export, Change Sets, Work, and MCP write-safe tools.

- [x] T025: Map Git/sync tests for R004; completion links current tests for
  remote profile, sync status/fetch/pull/push, proposal branch lifecycle, Work
  branch lifecycle, merge/finalize/cleanup, and conflict handling.

- [x] T026: Identify missing tests for R004; completion is a gap list for every
  responsibility group where extraction would be risky without additional
  tests.

### Phase 5 - Extraction Order And Facade Contract

- [x] T027: Define extraction risk criteria for R005; completion is a scoring
  scheme based on owner-governance sensitivity, storage sensitivity,
  Git/network side effects, CLI/MCP exposure, test coverage, and coupling.

- [x] T028: Produce staged extraction order for R005; completion is a plan that
  starts with architecture contract, inventory, permissions/consent, then
  additional services in a justified order, with CLI modularization delayed.

- [x] T029: Define `P2PWorkspace` delegation contract for R006; completion is a
  table of facade methods that will delegate to services while preserving
  signatures and return dataclasses.

- [x] T030: Define temporary-stay methods for R006; completion is a table of
  methods/helpers that should remain in `P2PWorkspace` until later extractions
  because of coupling or insufficient tests.

- [x] T031: Define separate-proposal methods for R006; completion is a table of
  behavior that cannot change without a new proposal, such as CLI/MCP breaking
  changes, storage layout changes, and governance/consent semantic changes.

### Phase 6 - Follow-Up Implementation Seeds

- [x] T032: Seed feature spec for permissions/consent extraction for R007;
  completion is a proposed feature name, requirement outline, design questions,
  and task seeds, without creating source changes.

- [x] T033: Seed feature specs for subsequent service extractions for R007;
  completion is a backlog of candidate local feature specs for proposal,
  readiness, project state, registry, work/sync, spec/export, intake/choice,
  and MCP/CLI modularization work.

- [x] T034: Define done criteria for future extraction features for R007;
  completion is reusable criteria covering no behavior drift, focused tests,
  facade delegation, unchanged storage, unchanged CLI/MCP surface, and
  validation.

### Phase 7 - Verification

- [x] T035: Verify no runtime source change; completion is a reviewed diff
  showing no changes under `src/` for this inventory feature.

- [x] T036: Run local validation appropriate for non-runtime spec changes;
  completion is reviewed command output, normally `.venv/bin/p2p validate`
  when P2P state changed or a documented reason when not run.

- [x] T037: Review task traceability; completion is every requirement R001-R007
  represented by at least one task and every task linked to an output artifact.

- [x] T038: Update task completion only with evidence; completion is checked
  tasks that point to `inventory.md`, docs, validation output, or reviewed diff
  evidence.

## Current Status

All tasks are checked. This feature now contains the technical inventory,
boundary map, compatibility test map, extraction order, facade contract,
follow-up feature seeds, and verification evidence needed before source
refactoring starts.
