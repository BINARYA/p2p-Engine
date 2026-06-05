# Requirements - Domain-Aware Visible Project Definition Export

## Scope

Replace the default software-spec centered export path with a domain-aware
project definition export path.

## Origin

- Source: owner request during local development.
- Related P2P direction: PROP-083 draft.

This spec is local implementation planning. It does not decide PROP-083 and does
not represent P2P governance state.

## In Scope

- Generate a detailed generic project definition for every project domain.
- Write the human-facing generic project definition to a visible root-level
  output directory.
- Restrict OpenSpec and Spec Kit exports to software-compatible projects or
  explicit software-compatible export profiles.
- Stop guiding CLI, MCP, skill, and docs users toward `software-spec` as the
  default project definition export path.

## Out Of Scope

- Removing P2P governance state.
- Removing all existing compatibility code in one step if a migration period is
  needed.
- Making P2P Engine implement code for downstream projects.
- Deciding P2P proposal acceptance.

## Functional Requirements

- R001: WHEN a user exports a project definition for any domain, THE SYSTEM
  SHALL generate a generic project definition.
- R002: WHEN the project domain is not software-compatible, THE SYSTEM SHALL NOT
  generate OpenSpec or Spec Kit exports by default.
- R003: IF the project domain is software-compatible or an explicit
  software-compatible export profile is selected, THEN THE SYSTEM SHALL allow
  OpenSpec and Spec Kit export targets.
- R004: WHEN a human-facing project definition is generated, THE SYSTEM SHALL
  write it under a visible root-level output directory instead of only under
  `.p2p/outputs`.
- R005: WHEN CLI help, MCP tool descriptions, skills, or docs describe project
  definition export, THE SYSTEM SHALL describe the domain-aware project
  definition workflow instead of the Change Set software-spec workflow.
- R006: WHEN legacy software-spec commands remain available, THE SYSTEM SHALL
  label them as compatibility or software-only workflows.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL preserve deterministic offline generation.
- N002: THE SYSTEM SHALL preserve source traceability from generated output back
  to accepted project memory.
- N003: THE SYSTEM SHALL keep internal provenance under P2P-managed state when
  needed, while making human-facing output visible.

## Edge Cases And Errors

- Non-software project requests `openspec`: fail with a clear domain/profile
  error unless explicitly overridden by a software-compatible profile.
- Non-software project requests `speckit`: fail with a clear domain/profile
  error unless explicitly overridden by a software-compatible profile.
- Existing `.p2p/outputs/software-spec/*` directories exist: do not delete them
  during export unless a separate cleanup is explicitly requested.

## Acceptance Criteria

- AC001: A non-software project can generate a generic project definition without
  creating `.p2p/outputs/software-spec/<CHANGE-ID>/`.
- AC002: A non-software project does not offer or produce OpenSpec/Spec Kit
  exports by default.
- AC003: A software-compatible project can explicitly generate generic,
  OpenSpec, and Spec Kit outputs.
- AC004: The primary generic output is visible from the project root.
- AC005: CLI tests cover generic export, non-software target rejection, and
  software-compatible target allowance.
- AC006: MCP tests cover the same behavior if MCP exposes the export workflow.
