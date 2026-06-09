# Tasks - Project Interaction Style

All tasks start open. Mark a task complete only with evidence from `src/`,
`tests/`, `docs/`, generated outputs, or observed CLI/MCP behavior.

- [x] T001: Review accepted `PROP-087`, this feature spec, existing
  project-state/project-vertical services, agent template generation, context,
  validation, CLI project commands, and MCP project handlers; completion is an
  implementation note or comments only where needed confirming final placement.
  Covers R001-R027, N001-N004.

- [x] T002: Add core interaction style dataclasses, constants, scale descriptors,
  defaults, and pure validation helpers; completion is focused unit tests for
  allowed values, labels, descriptions, defaults, and invalid inputs. Covers
  R001-R007, R020-R027, N005, AC001.

- [x] T003: Add `ProjectInteractionStyleService` with effective read,
  configured/default source reporting, partial set/update, schema validation,
  diagnostic errors, and atomic persistence; completion is service tests for
  R001-R007 and E001-E007. Covers R001-R007, N006-N008, AC001.

- [x] T004: Wire `P2PWorkspace` facade methods to the service without adding
  domain rules to `storage/filesystem.py`; completion is facade tests or service
  tests proving call shapes and return views. Covers N002-N004.

- [x] T005: Add `p2p project interaction-style show` CLI command and output
  formatter; completion is CLI tests for default fallback, configured state,
  path/source reporting, and malformed state failure. Covers R003, R008,
  E001-E007, AC002.

- [x] T006: Add `p2p project interaction-style set` CLI command with
  `--technical-verbosity`, `--formality`, `--assertiveness`, `--actor`, and
  `--root`; completion is CLI tests for full update, partial update, no-option
  failure, invalid values, and resulting output. Covers R004-R010, E003-E006,
  AC002.

- [x] T007: Add MCP catalog definitions, ordered registry entries, and project
  handler dispatch for `p2p_project_interaction_style_show` and
  `p2p_project_interaction_style_set`; completion is MCP tests proving schemas,
  read-only/write-safe descriptions, payload shapes, dispatch, and no mutation
  from show. Covers R011-R012, E008-E009, AC003.

- [x] T008: Add validation integration for present interaction style state;
  completion is validation tests for missing non-error state, malformed YAML,
  missing top-level key, invalid schema version, missing scales, and out-of-range
  values with recovery command. Covers R017-R018, E002-E007, AC004.

- [x] T009: Add compact context integration using an injected workspace/service
  callback; completion is context tests proving effective style values and
  allowed show/set commands appear without broad scans. Covers R015, R019,
  AC005.

- [x] T010: Update generated `AGENTS.md` content with a shared interaction style
  block; completion is snapshot/content tests proving CLI/MCP inspection,
  update guidance, scale semantics, and non-effect boundaries are present.
  Covers R013, R016, E010, AC006-AC007.

- [x] T011: Update generated Codex project skills and other adapter instruction
  templates with concise interaction style guidance; completion is generated
  content tests for Codex, Claude, Cursor, Copilot, Gemini, and generic outputs
  where supported. Covers R013, R016, E010, AC006.

- [x] T012: Update generated `.p2p/agent-policy.yml` payload with structured
  interaction style defaults, commands, MCP tools, affected surfaces, and
  non-affected authority/truth surfaces; completion is policy payload tests.
  Covers R014, R016, AC006-AC007.

- [x] T013: Update docs for interaction style CLI, MCP tools, scale semantics,
  defaults, validation behavior, and CLI/MCP-only mutation boundaries;
  completion is reviewed docs matching implemented behavior. Covers R008-R018,
  AC008.

- [x] T014: Add explicit tests or documented scenarios proving direct `.p2p`
  edits and temporary-file copy workarounds are not part of the supported style
  mutation workflow. Covers R002, R013, R016, E010, AC006.

- [x] T015: Verify interaction style does not alter readiness scores,
  readiness gates, owner-controlled governance decisions, permissions, consent,
  validation truth, or factual claims; completion is focused compatibility tests
  or unchanged existing tests plus a short implementation note. Covers R016,
  R027, AC007.

- [x] T016: Run focused test groups for core/service, CLI, MCP, validation,
  context, generated instructions, and readiness compatibility; completion is
  passing pytest output or documented failures with cause and next action.
  Covers AC001-AC008.

- [x] T017: Run broad project validation after implementation:
  `.venv/bin/p2p validate` plus the touched compatibility tests; completion is
  reviewed output or documented residual risk. Covers N001, AC008.

- [x] T018: Before considering the feature complete, verify every completed task
  has evidence from `src/`, `tests/`, `docs/`, generated outputs, or observed
  CLI/MCP behavior; completion is a final implementation note, not spec text
  alone. Covers local dev-spec policy and `ENGINEERING_QUALITY_SKILL.md`.
