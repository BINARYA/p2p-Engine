# P2PWorkspace Work Planning Helper Consolidation Requirements

## Scope

This local development feature consolidates YAML helper functions in
`services.work_planning` onto `foundation.files`.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL preserve strict YAML mapping semantics in Work planning.
- THE SYSTEM SHALL remove duplicated YAML serialization/parsing helpers from
  `services.work_planning`.
- THE SYSTEM SHALL not modify Work branch lifecycle behavior in this step.
- THE SYSTEM SHALL verify Work planning behavior with focused and full tests.

## Out Of Scope

- `services.work_branches`
- `services.proposal_branches`
- Git lifecycle behavior.
- Any `.p2p/` state edits.
