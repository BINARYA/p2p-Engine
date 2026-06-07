# P2PWorkspace Foundation Helper Service Consolidation 5 Requirements

## Scope

This local development feature consolidates helper functions in the remaining
audited lifecycle services that match `foundation.files` contracts.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL keep strict YAML mapping semantics for `changes` and `intake`.
- THE SYSTEM SHALL preserve the `changes` slug fallback `"item"`.
- THE SYSTEM SHALL not modify `project_maturity` because its YAML non-mapping
  error message intentionally differs from `foundation.files`.
- THE SYSTEM SHALL verify changed services with focused tests and the full test
  suite.

## Selected Services

- `services.changes`
- `services.intake`

## Out Of Scope

- `services.project_maturity`
- Proposal/Work branch services.
- Any `.p2p/` state edits.
