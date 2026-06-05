# Requirements - Managed Work Sync Permissions

## Scope

Capture Change Sets, Work manifests, managed Git operations, sync, permissions,
and consent receipts.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-013, PROP-014, PROP-015, PROP-030, PROP-031, PROP-032,
  PROP-033, PROP-034, PROP-035, PROP-036, PROP-037, PROP-038, PROP-039,
  PROP-040, PROP-041, PROP-043, PROP-066, PROP-072, PROP-073, PROP-075

## Functional Requirements

- R001: WHEN accepted intent becomes operational work, THE SYSTEM SHALL create
  metadata-only Change Sets and expose lifecycle/status/task inspection.
- R002: WHEN a validated export is handed off, THE SYSTEM SHALL create Work
  manifests without creating branches or commits.
- R003: WHEN managed Work progresses, THE SYSTEM SHALL support branch, submit,
  review, publish, request-review, accept, finalize, cleanup, retire, scan, and
  status commands with appropriate safety checks.
- R004: WHEN remote synchronization is configured, THE SYSTEM SHALL expose
  status, fetch, pull, and push commands.
- R005: WHEN owner-sensitive operations occur through permission-gated paths, THE
  SYSTEM SHALL require valid consent receipts and record use.
- R006: WHEN remote project metadata is configured, THE SYSTEM SHALL expose
  project remote show/configure behavior.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep Git details hidden from routine users unless
  needed for recovery/debug.
- N002: THE SYSTEM SHALL require clean worktree or explicit recovery paths for
  branch/merge-sensitive operations.

## Acceptance Criteria

- AC001: CLI tests cover Change Set creation/status/policy/lifecycle.
- AC002: CLI tests cover Work plan through cleanup lifecycle.
- AC003: CLI and MCP tests cover sync, remote profile, permissions, and consent.
