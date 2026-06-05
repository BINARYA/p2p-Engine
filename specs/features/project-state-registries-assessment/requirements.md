# Requirements - Project State Registries Assessment

## Scope

Define generated project state, registries, validation, rubrics, readiness
assessment, maturity assessment, and operational brief behavior.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-010, PROP-011, PROP-016, PROP-022, PROP-023, PROP-053,
  PROP-054, PROP-056, PROP-057, PROP-079, PROP-081

## Functional Requirements

- R001: WHEN accepted project memory changes, THE SYSTEM SHALL refresh
  rationalized project state.
- R002: WHEN project state is inspected, THE SYSTEM SHALL show overview,
  problem, scope, SWOT, or feature sections.
- R003: WHEN registries are refreshed, THE SYSTEM SHALL generate proposal,
  decision, change, choice, relation, artifact, and readiness indexes.
- R004: WHEN validation runs, THE SYSTEM SHALL report errors, warnings, and
  infos without mutating unrelated state.
- R005: WHEN rubrics or maturity are requested, THE SYSTEM SHALL initialize and
  assess project definition maturity.
- R006: WHEN operational brief or next actions are used, THE SYSTEM SHALL expose
  prompt/import/show and managed next-action lifecycle commands.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL generate deterministic artifacts from source memory.
- N002: THE SYSTEM SHALL keep generated registries as derived indexes.

## Acceptance Criteria

- AC001: CLI tests cover project refresh/status/show.
- AC002: CLI tests cover registry refresh/status/show.
- AC003: CLI and MCP tests cover validation, rubrics, maturity, next actions,
  and operational brief surfaces.
