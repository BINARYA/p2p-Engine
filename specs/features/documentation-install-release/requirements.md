# Requirements - Documentation Install Release

## Scope

Capture public documentation, installation guidance, agent setup docs,
project-local wheel installation, and automated release publishing.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-058, PROP-061, PROP-062, PROP-067, PROP-068, PROP-069,
  PROP-070, PROP-078, PROP-080

## Functional Requirements

- R001: WHEN users read the repository entry point, THE SYSTEM SHALL explain what
  P2P Engine is, who it serves, and where detailed docs live.
- R002: WHEN users install P2P Engine, THE SYSTEM SHALL provide project-local
  installation guidance.
- R003: WHEN users connect agents through MCP, THE SYSTEM SHALL document client
  setup and stdio behavior.
- R004: WHEN maintainers release P2P Engine, THE PROJECT SHALL provide a package
  entrypoint and automated GitHub release wheel workflow.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep target-project setup separate from contributing to
  the P2P Engine repository.
- N002: THE SYSTEM SHALL not imply MCP exposes privileged operations unless the
  permission model supports them.

## Acceptance Criteria

- AC001: README, install docs, MCP docs, and agent docs exist.
- AC002: `pyproject.toml` exposes `p2p` and `p2p-mcp-server` entry points.
- AC003: release workflow exists for publishing wheel/sdist artifacts.
