# Requirements - Domain-Aware Visible Project Definition Export

## Origin

- Source P2P proposal: `PROP-083 - Domain-Aware Visible Project Definition Export`
- Decision: accepted by owner with readiness override after missing readiness gaps were resolved.

This spec is local implementation planning. P2P governance state remains under
`.p2p/`; generated visible project outputs are derived artifacts.

## Scope

Implement the accepted `PROP-083` behavior: a domain-generic, human-facing
project definition export written to a visible root-level `outputs/` tree, with
review snapshots and nested specialized export profiles.

## Functional Requirements

- R001: WHEN a user runs the default project definition export, THE SYSTEM SHALL
  generate `outputs/latest/project.md`.
- R002: THE SYSTEM SHALL make `outputs/latest/project.md` a single chaptered
  Markdown document for humans.
- R003: THE SYSTEM SHALL keep the default project definition domain-generic and
  SHALL NOT assume the project is software.
- R004: THE SYSTEM SHALL synthesize the default project definition from accepted
  P2P memory and current project state where available.
- R005: THE SYSTEM SHALL include source/generation metadata in the generated
  document showing that `.p2p/` remains the managed source of truth.
- R006: WHEN `outputs/latest/` already exists and a new default export is run,
  THE SYSTEM SHALL preserve the previous latest output under the next
  deterministic `outputs/review-###/` directory before writing the new latest.
- R007: THE SYSTEM SHALL support nested specialized export profile directories
  under `outputs/latest/exports/<profile-or-vertical>/`.
- R008: THE SYSTEM SHALL treat software-oriented outputs as specialized profiles
  rather than the default project definition.
- R009: THE SYSTEM SHALL preserve existing `.p2p/outputs` and `p2p spec export`
  behavior as compatibility behavior unless a separate explicit migration
  removes it.
- R010: THE SYSTEM SHALL expose the default visible export through a project-level
  CLI command, not only through Change Set software-spec commands.
- R011: IF MCP exposes project export functionality, THEN THE SYSTEM SHALL expose
  the visible default export without requiring a Change Set.
- R012: WHEN export status is requested, THE SYSTEM SHALL report the latest
  visible project definition path and existing review snapshots.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL generate outputs deterministically from local project
  state without network access.
- N002: THE SYSTEM SHALL avoid writing generated project output outside the
  repository root.
- N003: THE SYSTEM SHALL keep `.p2p/` as the source of truth and SHALL NOT read
  generated `outputs/` files as governance state.
- N004: THE SYSTEM SHALL preserve public CLI/MCP compatibility for existing spec
  export commands.
- N005: THE SYSTEM SHALL use cohesive services/renderers instead of adding large
  new domain behavior directly to `P2PWorkspace` or `cli.py`.

## Edge Cases And Errors

- E001: IF `outputs/latest/` does not exist, THEN the first export SHALL create
  it without creating an empty review snapshot.
- E002: IF `outputs/review-001/` already exists, THEN the next archived snapshot
  SHALL use the first available incrementing number.
- E003: IF `outputs/latest/` exists but is empty, THEN the export MAY replace it
  without archiving an empty snapshot.
- E004: IF a generated path cannot be written, THEN the command SHALL fail with
  a clear filesystem error instead of silently ignoring the export.
- E005: Existing `.p2p/outputs/spec-export/...` directories SHALL NOT be deleted
  by the visible project export.

## Acceptance Criteria

- AC001: Running the project-level export command creates
  `outputs/latest/project.md`.
- AC002: Re-running the export archives the previous latest output into
  `outputs/review-001/` and writes a new `outputs/latest/project.md`.
- AC003: The generated `project.md` contains source/generation metadata and
  chapters for purpose, scope, proposals/decisions, requirements, risks,
  assumptions, open questions, readiness, and delivery/export context.
- AC004: Existing `p2p spec export` tests continue to pass and continue writing
  compatibility exports under `.p2p/outputs/spec-export/...`.
- AC005: CLI tests cover default visible export creation, review snapshot
  creation, and status reporting.
- AC006: MCP tests cover visible export creation/status if MCP tools are added.
