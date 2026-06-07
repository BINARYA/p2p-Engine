# P2PWorkspace Proposal Prompt Artifact Service Extraction Tasks

## Phase 1 - Scope And Test Map

- [x] T001: Reassess `filesystem.py` after governance service extraction.

- [x] T002: Select proposal prompt/artifact behavior as the next bounded
  extraction because it has clear facade methods and isolated CLI/MCP
  consumers.

- [x] T003: Map consumers: prompt CLI command module, collaboration impact
  commands, MCP prompt tools, and skeleton tests.

- [x] T004: Define out-of-scope boundaries: no prompt template changes, no
  proposal document lifecycle changes, no readiness/decision/branch/governance
  changes, no CLI/MCP formatting changes.

## Phase 2 - Focused Tests First

- [x] T005: Add direct service test for prompt generation path and rendered
  content context.

- [x] T006: Add direct service test for exploration file import and exploration
  status quality classification.

- [x] T007: Add direct service test for exploration directory import and empty
  directory error.

- [x] T008: Add direct service test for `import_artifact()` target mapping and
  task YAML validation.

- [x] T009: Add direct service test for impact file and directory imports with
  YAML key validation.

## Phase 3 - Service Extraction

- [x] T010: Create `src/p2p_engine/services/proposal_artifacts.py` with
  dataclasses, prompt/import kinds, renderers, validators, and local helpers.

- [x] T011: Move prompt context assembly and renderer dispatch into
  `ProposalArtifactService`.

- [x] T012: Move exploration import/status behavior into the service.

- [x] T013: Move generic generated artifact import behavior into the service.

- [x] T014: Move impact artifact import behavior into the service.

- [x] T015: Add lazy `P2PWorkspace` proposal artifact service factory.

- [x] T016: Delegate existing `P2PWorkspace` prompt/artifact methods to the
  service.

- [x] T017: Remove now-unused exploration status dataclasses/constants/helpers
  from `storage/filesystem.py`.

## Phase 4 - Compatibility Verification

- [x] T018: Run focused proposal artifact service tests.

- [x] T019: Run focused prompt/exploration/impact CLI tests.

- [x] T020: Run focused MCP prompt tool tests.

- [x] T021: Run skeleton prompt/exploration tests.

- [x] T022: Run `.venv/bin/p2p validate`.

- [x] T023: Run the full test suite.

## Phase 5 - Traceability And Completion

- [x] T024: Review source scope with `git status --short`.

- [x] T025: Confirm no prompt template, CLI/MCP formatting, branch/sync,
  readiness, decision, governance, or proposal document behavior changed.

- [x] T026: Update `requirements.md` statuses after verification.

- [x] T027: Record implementation evidence in `design.md`.

- [x] T028: Update the global refactoring tracker.

- [x] T029: Mark all tasks complete only after evidence exists.

## Current Status

Completed.
