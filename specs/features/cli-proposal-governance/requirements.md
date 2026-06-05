# Requirements - CLI Proposal Governance

## Scope

Define the local implementation expectations for the core CLI, proposal
creation/inspection, contributions, decisions, and governance helper commands.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-001, PROP-005, PROP-009, PROP-019, PROP-020, PROP-052

## Functional Requirements

- R001: WHEN a user initializes a project, THE SYSTEM SHALL create the local P2P
  workspace and baseline agent instructions.
- R002: WHEN a user creates a proposal, THE SYSTEM SHALL persist a draft
  proposal with inspectable problem, proposal, and acceptance content.
- R003: WHEN a user lists or shows proposals, THE SYSTEM SHALL provide a compact
  read-only view without requiring direct file inspection.
- R004: WHEN a user accepts, rejects, or defers a proposal, THE SYSTEM SHALL
  record the owner decision through explicit commands.
- R005: WHEN a user adds proposal contributions, THE SYSTEM SHALL preserve them
  without deciding the proposal.
- R006: WHEN a user initializes or inspects governance helper artifacts, THE
  SYSTEM SHALL expose CLI commands for governance, votes, SWOT prompts, and
  precedents.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep governance decisions owner-controlled.
- N002: THE SYSTEM SHALL keep direct `.p2p` internals hidden behind public CLI or
  explicit MCP tools.

## Acceptance Criteria

- AC001: CLI tests cover init, proposal create, prompt flow, list/show, and
  decision shortcuts.
- AC002: CLI tests cover contribution listing.
- AC003: CLI command definitions exist for governance, vote, SWOT, and precedent
  surfaces.
