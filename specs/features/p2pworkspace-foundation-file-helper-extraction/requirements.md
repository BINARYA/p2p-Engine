# P2PWorkspace Foundation File Helper Extraction Requirements

## Scope

This local development feature continues the `P2PWorkspace` modular refactoring
after Work review suggestion ownership moved to `services.work_branches`. It
extracts generic slug/path/YAML helpers from `storage.filesystem` into a
foundation module and updates the facade to consume that shared foundation
surface.

## Requirements

- THE SYSTEM SHALL preserve public `P2PWorkspace` behavior.
- THE SYSTEM SHALL move generic slug, YAML dump/read, YAML mapping, and relative
  path helpers out of `storage.filesystem`.
- THE SYSTEM SHALL keep facade-specific messages, such as duplicate proposal ID
  validation text, in `storage.filesystem` unless and until a service owns the
  full message contract.
- THE SYSTEM SHALL add focused tests for the new foundation helper module.
- THE SYSTEM SHALL avoid broad cross-service helper consolidation in this step.

## Out Of Scope

- No `.p2p/` state edits.
- No CLI/MCP contract changes.
- No mass replacement of duplicate YAML helpers across every service module.
