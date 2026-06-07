# P2PWorkspace Work Review Suggestion Helper Extraction Requirements

## Scope

This local development feature continues the `P2PWorkspace` modular refactoring
after callback rewiring. It removes Work review suggestion URL helpers from
`storage.filesystem` and moves ownership to the Work branch service.

## Requirements

- THE SYSTEM SHALL preserve public `P2PWorkspace` work branch behavior.
- WHEN a Work external review request is created, THE SYSTEM SHALL continue to
  generate provider-specific GitHub and GitLab suggestions from the configured
  remote URL and branch name.
- THE SYSTEM SHALL keep test override support for review suggestions when a
  focused test needs deterministic custom output.
- THE SYSTEM SHALL remove Work review suggestion helper functions from
  `storage.filesystem`.
- THE SYSTEM SHALL keep `storage.filesystem` as a service composition facade,
  not the owner of Work branch review URL formatting.

## Out Of Scope

- No CLI/MCP contract changes.
- No proposal branch review suggestion refactor.
- No broad YAML/slug helper consolidation.
