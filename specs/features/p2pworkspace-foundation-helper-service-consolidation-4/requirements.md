# P2PWorkspace Foundation Helper Service Consolidation 4 Requirements

## Scope

This local development feature continues helper consolidation for larger
lifecycle services after auditing YAML strictness and slug fallback behavior.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL keep strict YAML mapping semantics for the selected services.
- THE SYSTEM SHALL preserve proposal slug fallback `"project"` and choice slug
  fallback `"item"`.
- THE SYSTEM SHALL extend `foundation.files.slugify` with an optional fallback
  parameter without changing its default behavior.
- THE SYSTEM SHALL leave `changes` and `intake` for a later tranche because they
  need separate lifecycle-focused verification.

## Selected Services

- `services.proposals`
- `services.readiness`
- `services.choices`

## Out Of Scope

- `services.changes`
- `services.intake`
- `services.project_maturity`
- Any `.p2p/` state edits.
