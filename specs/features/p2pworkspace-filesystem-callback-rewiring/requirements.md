# P2PWorkspace Filesystem Callback Rewiring Requirements

## Scope

This local development feature continues the `P2PWorkspace` modular refactoring
after unused facade wrapper cleanup. It rewires service constructor callbacks in
`storage.filesystem` so they point directly to service-owned methods where that
can be done without changing public behavior.

## Requirements

- THE SYSTEM SHALL preserve every public `P2PWorkspace` method and existing CLI
  and MCP behavior.
- WHEN a service callback currently points to a private `P2PWorkspace`
  pass-through wrapper, THE SYSTEM SHALL rewire it to the owning service method
  if doing so does not introduce circular construction.
- WHEN tests instantiate services directly, THE TESTS SHALL use service-owned
  collaborators instead of removed private `P2PWorkspace` wrappers.
- THE SYSTEM SHALL remove private callback wrappers from `P2PWorkspace` only
  after all active callers have been rewired.
- THE SYSTEM SHALL keep `storage.filesystem` as the compatibility facade and
  service composition layer.
- THE SYSTEM SHALL verify behavior with focused service tests, focused CLI/MCP
  regressions, `p2p validate`, and the full pytest suite.

## Out Of Scope

- No public command changes.
- No `.p2p/` state edits.
- No service API redesign beyond passing existing service methods directly.
