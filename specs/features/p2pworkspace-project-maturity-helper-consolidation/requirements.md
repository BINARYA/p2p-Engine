# P2PWorkspace Project Maturity Helper Consolidation Requirements

## Scope

This local development feature consolidates `services.project_maturity` YAML
helpers onto `foundation.files` while preserving its distinct YAML non-mapping
error message.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL preserve `project_maturity` non-mapping YAML errors as
  `YAML document must be a mapping: <path>`.
- THE SYSTEM SHALL keep the default `foundation.files.read_yaml_mapping` error
  message unchanged for existing callers.
- THE SYSTEM SHALL remove duplicated YAML helper definitions from
  `services.project_maturity`.
- THE SYSTEM SHALL verify behavior with focused tests and the full test suite.

## Out Of Scope

- Proposal branch, Work branch, and Work planning helper consolidation.
- Any `.p2p/` state edits.
