# Requirements - Agent Integration Registry

## Scope

Capture generated agent instructions, adapter installation lifecycle, registry,
drift handling, and MCP parity for agent integration operations.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Current export focus: CHANGE-065 / PROP-006
- Source proposals: PROP-005, PROP-006, PROP-021, PROP-045, PROP-046, PROP-067,
  PROP-068, PROP-069, PROP-070, PROP-074

## Functional Requirements

- R001: WHEN a project is initialized without narrowing agents, THE SYSTEM SHALL
  install generic, Codex, Claude, Cursor, Copilot, Gemini, and OpenCode local
  instructions where applicable.
- R002: WHEN a user narrows agents during init, THE SYSTEM SHALL always include
  the generic baseline.
- R003: WHEN agent integrations are installed, THE SYSTEM SHALL write
  `.p2p/agent-integrations.yml` with adapter metadata and managed file records.
- R004: WHEN an agent file has drifted, THE SYSTEM SHALL refuse unsafe update or
  uninstall unless forced/safe.
- R005: WHEN users inspect or manage integrations, THE SYSTEM SHALL expose
  `agent list/show/install/update/uninstall/doctor`.
- R006: WHEN MCP clients manage agent integrations, THE SYSTEM SHALL expose
  equivalent safe tools.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL NOT store active/default/preferred/current agent state.
- N002: THE SYSTEM SHALL preserve shared generic files when uninstalling
  adapter-specific files.

## Acceptance Criteria

- AC001: CLI tests cover default all-agent init.
- AC002: CLI tests cover narrowed agent init with generic baseline.
- AC003: CLI tests cover drift-safe update and uninstall.
- AC004: MCP tests cover agent integration lifecycle tools.
