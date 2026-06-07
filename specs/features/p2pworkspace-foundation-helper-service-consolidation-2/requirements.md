# P2PWorkspace Foundation Helper Service Consolidation 2 Requirements

## Scope

This local development feature continues incremental consolidation of helper
functions onto `foundation.files`. It targets a second low-risk tranche while
preserving the difference between strict and tolerant YAML mapping readers.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL preserve tolerant YAML mapping behavior in services that
  currently return the supplied default for missing or non-mapping YAML files.
- THE SYSTEM SHALL add a foundation helper for tolerant YAML mapping reads before
  replacing local tolerant readers.
- THE SYSTEM SHALL replace duplicated YAML dump helpers and identity slug helpers
  only where behavior remains equivalent.
- THE SYSTEM SHALL avoid changing large lifecycle services in this tranche.

## Selected Services

- `services.remote_profile`
- `services.permissions`
- `services.consent`
- `services.project_state`

## Out Of Scope

- Strict reader replacement in services whose malformed YAML error behavior is
  domain-specific.
- Proposal, Work, Change, Choice, Intake, Registry, Readiness, and Governance
  service consolidation.
- Any `.p2p/` state edits.
