# P2PWorkspace Project Maturity Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract project definition rubrics and maturity assessment behavior from
`P2PWorkspace` into a cohesive runtime service while preserving CLI, MCP, and
workspace facade compatibility.

## Requirements

- [x] R001: `P2PWorkspace.init_project_rubrics()`,
  `init_project_rubrics_preview()`, `show_project_rubrics()`,
  `refresh_definition_maturity()`, and `show_definition_maturity()` must keep
  the same public behavior and return shapes.

- [x] R002: `ProjectRubrics` and `ProjectDefinitionMaturity` must remain
  import-compatible from `p2p_engine.storage.filesystem`.

- [x] R003: Rubrics initialization must continue writing
  `.p2p/project/rubrics.yml`, `.p2p/project/domain.yml`, and the `project.domain`
  value in `.p2p/project.yml`.

- [x] R004: Rubrics preview must continue returning only criterion dictionaries
  and must not write files.

- [x] R005: Maturity refresh must continue computing coverage from proposal and
  decision evidence, writing `.p2p/project/maturity-assessment.yml`, and must
  not assess implementation completeness.

- [x] R006: Unresolved or missing rubrics must continue producing
  `rubric_missing`, score `0`, and the same gap/suggested-action semantics.

- [x] R007: The service must not import Typer, Rich, MCP handlers, JSON-RPC,
  Git/sync, branch lifecycle services, validation, registry generation, or
  agent instruction generation.

- [x] R008: Existing CLI and MCP maturity/rubrics behavior must remain
  compatible.

## Non-Goals

- Changing built-in rubric content or scoring thresholds.
- Moving project initialization as a whole.
- Moving agent instruction or agent integration behavior.
- Editing `.p2p/` managed project state by hand.
