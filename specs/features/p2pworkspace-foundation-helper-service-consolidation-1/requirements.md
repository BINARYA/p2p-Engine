# P2PWorkspace Foundation Helper Service Consolidation 1 Requirements

## Scope

This local development feature starts incremental consolidation of duplicated
YAML/path/slug helpers across service modules after `foundation.files` was
introduced. It targets a first low-risk service tranche only.

## Requirements

- THE SYSTEM SHALL preserve all public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL replace duplicated YAML helper implementations in selected
  low-risk services with imports from `foundation.files`.
- THE SYSTEM SHALL keep each service's domain validation and error messages
  unchanged.
- THE SYSTEM SHALL avoid broad mechanical replacement across large lifecycle
  services in this step.
- THE SYSTEM SHALL verify each changed service with focused tests and the full
  test suite.

## Selected Services

- `services.conflicts`
- `services.project_assessment`
- `services.next_actions`

## Out Of Scope

- Proposal, Work branch, choice, intake, registry, readiness, and governance
  helper consolidation.
- Any `.p2p/` state edits.
- Any public command contract changes.
