# P2PWorkspace Filesystem Facade Wrapper Cleanup Requirements

## Scope

This local development feature continues the `P2PWorkspace` modular refactoring
after dead helper cleanup. It removes private pass-through wrappers from
`storage.filesystem` only when they have no active callers and their behavior is
already owned by an extracted service.

## Requirements

- THE SYSTEM SHALL preserve all public `P2PWorkspace` methods and return types.
- THE SYSTEM SHALL keep private wrappers that are still used as service callback
  dependencies or by focused service tests until those collaborators are
  explicitly rewired in a separate task.
- WHEN a private `P2PWorkspace` helper has no active caller, THE SYSTEM SHALL
  remove it if the equivalent service method remains available.
- WHEN cleanup is complete, THE SYSTEM SHALL keep `storage.filesystem` as a
  compatibility facade and service composition layer, not as an owner of
  duplicated runtime behavior.
- THE SYSTEM SHALL verify behavior with focused service, CLI, MCP, validation,
  and full test runs.

## Out Of Scope

- No public CLI or MCP behavior changes.
- No `.p2p/` state edits.
- No broad service constructor rewiring unless required by a removed wrapper.
