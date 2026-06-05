# Requirements - Intake Choice Conflict Next

## Scope

Capture raw idea intake, advisory overlap analysis, choices, explicit blockers,
conflicts, impact prompts, and next-action routing.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-012, PROP-017, PROP-018, PROP-024, PROP-025, PROP-050,
  PROP-079

## Functional Requirements

- R001: WHEN a raw idea is submitted, THE SYSTEM SHALL generate an intake prompt
  and record imported intake analysis.
- R002: WHEN intake recommendations are applied, THE SYSTEM SHALL provide a
  controlled plan/show/run workflow.
- R003: WHEN a project choice is needed, THE SYSTEM SHALL create, list, show,
  decide, discover, block, and unblock choices through explicit commands.
- R004: WHEN impact or conflict context is needed, THE SYSTEM SHALL expose
  prompt/import and conflict record/status workflows.
- R005: WHEN users ask what to do next, THE SYSTEM SHALL combine curated and
  generated next actions without making owner decisions.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep intake, choice discovery, impact, and next actions
  advisory unless an explicit command mutates state.
- N002: THE SYSTEM SHALL not decide choices automatically.

## Acceptance Criteria

- AC001: CLI tests cover intake prompt/import/status/apply.
- AC002: CLI tests cover choice lifecycle, discovery, blocking, and next-action
  integration.
- AC003: CLI/MCP tests cover conflict and impact advisory/read behavior.
