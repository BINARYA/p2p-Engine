# P2PWorkspace Modular Refactoring Contract Tasks

## Tasks

### Phase 1 - Agent Contract

- [x] T001: Review current `AGENTS.md` architecture/development content;
  completion is a short note identifying where the PROP-059 rules should be
  inserted without weakening existing P2P governance boundaries.

- [x] T002: Implement R001 hard rule in `AGENTS.md` that new unrelated domain
  logic must not be added directly to `src/p2p_engine/cli.py`,
  `src/p2p_engine/storage/filesystem.py`, or `src/p2p_engine/mcp/tools.py` by
  default; completion is concise wording that points agents to dedicated
  services/adapters or existing local specs.

- [x] T003: Implement R001 compatibility exception wording in `AGENTS.md`;
  completion is explicit guidance that the large files may still receive
  facade, orchestration, compatibility, or small command glue changes when
  justified by an accepted spec.

- [x] T004: Implement R001 governance separation wording in `AGENTS.md`;
  completion is explicit guidance that architecture rules do not authorize
  agents to bypass P2P owner-controlled decisions, consent, or managed state
  boundaries.

### Phase 2 - Development Guidelines

- [x] T005: Create `docs/DEVELOPMENT-GUIDELINES.md` skeleton for R002;
  completion is a document with sections for purpose, current architecture,
  target architecture, module ownership, feature rules, anti-patterns,
  compatibility, testing, and roadmap.

- [x] T006: Document current architecture for R002; completion is a concise
  description of `cli.py`, `P2PWorkspace`, `filesystem.py`, `mcp/tools.py`,
  `storage/git.py`, `core/`, `exporters/`, `prompts/`, `tests/test_cli.py`, and
  `tests/test_mcp.py`.

- [x] T007: Document target layering for R002 and R003; completion is a clear
  separation between domain rules, application services/use cases, adapters,
  facade, CLI presentation, and MCP schema/transport.

- [x] T008: Document module ownership rules for R002; completion is guidance
  for where future code should go, including `services/`, `adapters/`,
  possible `cli_commands/`, and MCP registry/dispatch surfaces.

- [x] T009: Document anti-patterns for R002; completion is a list covering
  monolithic additions to `filesystem.py`, business logic in CLI handlers,
  schema and dispatch coupling in MCP, duplicated YAML/Markdown parsing, silent
  Git errors, and consent bypass.

### Phase 3 - Compatibility Contract

- [x] T010: Implement R003 facade guidance in
  `docs/DEVELOPMENT-GUIDELINES.md`; completion is explicit wording that
  `P2PWorkspace` remains the compatibility facade while new services are
  introduced behind it.

- [x] T011: Implement R004 CLI compatibility guidance; completion is a list of
  command names, option semantics, human output, JSON output, and exit behavior
  as compatibility-sensitive unless a separate proposal approves a change.

- [x] T012: Implement R004 MCP compatibility guidance; completion is a list of
  tool names, schemas, payloads, permission classes, and JSON-RPC behavior as
  compatibility-sensitive.

- [x] T013: Implement R004 storage compatibility guidance; completion is a list
  of `.p2p` paths, YAML/Markdown shapes, generated registries, validation
  findings, and project refresh outputs as compatibility-sensitive.

- [x] T014: Implement R004 consent/Git/sync compatibility guidance; completion
  is a list of consent receipt lifecycle, audit commits, permission-gated tool
  requirements, Git branch operations, sync operations, and error behavior as
  compatibility-sensitive.

### Phase 4 - Roadmap

- [x] T015: Implement R005 service-before-CLI roadmap; completion is a staged
  order that extracts internal services/use cases before splitting CLI command
  modules.

- [x] T016: Implement R006 first extraction rationale; completion is a roadmap
  section selecting permissions/consent first and explaining boundary clarity,
  safety value, lower presentation exposure, and test coverage.

- [x] T017: Add follow-up references to the inventory feature; completion is a
  link from the development guidelines roadmap to
  `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/`.

- [x] T018: Decide roadmap file placement; completion is either roadmap content
  embedded in `docs/DEVELOPMENT-GUIDELINES.md` or a linked
  `docs/REFACTORING-ROADMAP.md` with a clear owner decision recorded in the
  local docs.

### Phase 5 - Verification

- [x] T019: Verify R007 no runtime source change; completion is a reviewed diff
  showing no changes under `src/` for this first deliverable.

- [x] T020: Run `.venv/bin/p2p validate`; completion is reviewed output with no
  errors.

- [x] T021: Review local specs consistency; completion is `requirements.md`,
  `design.md`, and `tasks.md` aligned for both refactoring contract and
  inventory-map features.

- [x] T022: Mark completed tasks only after evidence exists; completion is
  checklist updates with references to changed docs or validation output.

## Current Binding Status

All tasks are checked. The documentation contract is implemented through
`AGENTS.md` and `docs/DEVELOPMENT-GUIDELINES.md`, with verification evidence in
`design.md`.
