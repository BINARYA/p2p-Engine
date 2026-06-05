# Requirements - MCP Tool Surface

## Scope

Capture the MCP server and tool surface for read-only, write-safe, advisory, and
permission-gated operations.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-044, PROP-046, PROP-048, PROP-049, PROP-050, PROP-052,
  PROP-065, PROP-066, PROP-075, PROP-077, PROP-081

## Functional Requirements

- R001: WHEN an MCP client lists tools, THE SYSTEM SHALL expose the safe P2P tool
  surface with structured schemas.
- R002: WHEN MCP clients call read tools, THE SYSTEM SHALL return structured
  project/proposal/change/work/context/registry data without direct file reads.
- R003: WHEN MCP clients call write-safe tools, THE SYSTEM SHALL perform only the
  named safe operation.
- R004: WHEN MCP clients request owner-sensitive operations, THE SYSTEM SHALL
  require matching consent receipts.
- R005: WHEN prompt/advisory MCP tools are called, THE SYSTEM SHALL generate
  prompts without importing outputs or making decisions.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep MCP as a structured interface over core behavior,
  not a bypass around governance.
- N002: THE SYSTEM SHALL reject unsupported or unauthorized operations
  explicitly.

## Acceptance Criteria

- AC001: MCP tests verify the exposed tool names.
- AC002: MCP tests verify write-safe bootstrap, proposal, agent, next-action,
  spec/export, and work-plan operations.
- AC003: MCP tests verify permission-gated operations require and consume
  consent.
