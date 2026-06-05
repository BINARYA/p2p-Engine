# Requirements - Proposal Readiness And Prompts

## Scope

Capture proposal readiness assessment and prompt-only advisory workflows.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-002, PROP-004, PROP-021, PROP-054, PROP-055, PROP-082

## Functional Requirements

- R001: WHEN a proposal needs readiness inspection, THE SYSTEM SHALL expose
  show, init, refresh, and explain commands.
- R002: WHEN readiness is weak or incomplete, THE SYSTEM SHALL expose gaps,
  failed gates, confidence, and suggested next actions.
- R003: WHEN users need AI/human assistance, THE SYSTEM SHALL generate prompt
  files for explore, digest, clarify, synthesize, plan, tasks, SWOT, impact, and
  spec refinement workflows.
- R004: WHEN prompt output is imported for supported phases, THE SYSTEM SHALL
  validate and store the imported result through CLI commands.
- R005: WHEN agents need bounded context, THE SYSTEM SHALL expose compact
  context before broad file reads.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL not invoke AI providers directly.
- N002: THE SYSTEM SHALL not let readiness scores decide governance outcomes.

## Acceptance Criteria

- AC001: CLI tests cover readiness status, refresh, and explain.
- AC002: CLI tests cover prompt-only import through task generation.
- AC003: MCP tests expose readiness and prompt tools as advisory/read-safe or
  write-safe where appropriate.
