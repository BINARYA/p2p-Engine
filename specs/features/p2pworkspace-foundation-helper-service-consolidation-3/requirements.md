# P2PWorkspace Foundation Helper Service Consolidation 3 Requirements

## Scope

This local development feature continues incremental consolidation of helper
functions onto `foundation.files`. It targets a third service tranche after
auditing strict versus tolerant YAML semantics.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL consolidate only services whose helper behavior matches an
  existing `foundation.files` helper contract.
- THE SYSTEM SHALL use tolerant YAML reads for services that currently fall back
  to defaults on non-mapping YAML.
- THE SYSTEM SHALL use strict YAML reads for services that currently raise on
  non-mapping YAML with the standard `"Invalid YAML mapping"` message.
- THE SYSTEM SHALL not alter `services.project_maturity` in this tranche because
  it has a distinct non-mapping YAML error message.

## Selected Services

- `services.software_spec`
- `services.registries`
- `services.agent_instructions`

## Out Of Scope

- `services.project_maturity`
- Large lifecycle services not audited in this tranche.
- Any `.p2p/` state edits.
