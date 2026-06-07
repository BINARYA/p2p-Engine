# P2PWorkspace Proposal Branch Helper Consolidation Requirements

## Scope

This local development feature consolidates local file YAML and slug helpers in
`services.proposal_branches` onto `foundation.files`.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL preserve proposal branch slug fallback behavior, where empty
  slugs are later handled by call-site fallbacks such as `"proposal"` or
  `"local"`.
- THE SYSTEM SHALL preserve tolerant local metadata YAML reads.
- THE SYSTEM SHALL not change YAML parsing of metadata loaded from Git refs as
  raw text.
- THE SYSTEM SHALL verify proposal branch lifecycle behavior with focused and
  full tests.

## Out Of Scope

- Work branch helper consolidation.
- Git lifecycle behavior changes.
- Any `.p2p/` state edits.
