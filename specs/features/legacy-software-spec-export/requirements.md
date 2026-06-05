# Requirements - Legacy Software Spec Export

## Scope

Document the currently implemented software-spec and spec-export workflow as
existing behavior, while distinguishing it from the desired future
domain-aware project definition export.

## Origin

- Generic export: `.p2p/outputs/spec-export/CHANGE-065/generic/project.md`
- Source proposals: PROP-026, PROP-027, PROP-028, PROP-029, PROP-064
- Related correction feature: `domain-aware-visible-project-definition-export`

## Functional Requirements

- R001: WHEN a user refreshes a software spec for a Change Set, THE SYSTEM SHALL
  generate the required software-spec artifact set.
- R002: WHEN a user exports a software spec, THE SYSTEM SHALL support generic,
  OpenSpec, and Spec Kit target outputs.
- R003: WHEN a user validates an export, THE SYSTEM SHALL check required target
  files and generic project definition sections.
- R004: WHEN a user asks for software-spec status/show/prompt/import, THE SYSTEM
  SHALL expose those compatibility commands.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL preserve source traceability from software-spec outputs
  to Change Sets and proposals.
- N002: THE SYSTEM SHOULD NOT be treated as the future default project
  definition export path.

## Acceptance Criteria

- AC001: CLI tests cover software-spec refresh, prompt, import, status, show,
  export, export-show, and export-validate.
- AC002: MCP tests cover write-safe spec export and work plan.
