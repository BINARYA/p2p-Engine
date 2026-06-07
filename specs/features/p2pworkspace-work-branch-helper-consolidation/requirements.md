# P2PWorkspace Work Branch Helper Consolidation Requirements

## Scope

This local development feature consolidates local file YAML helpers in
`services.work_branches` onto `foundation.files`.

## Requirements

- THE SYSTEM SHALL preserve public CLI, MCP, and `P2PWorkspace` behavior.
- THE SYSTEM SHALL preserve tolerant local Work manifest YAML reads.
- THE SYSTEM SHALL preserve raw Git-ref YAML parsing behavior for manifests read
  from branch content.
- THE SYSTEM SHALL not change Work branch Git lifecycle behavior.
- THE SYSTEM SHALL verify Work branch lifecycle behavior with focused and full
  regression tests.

## Out Of Scope

- Proposal branch behavior.
- Git adapter behavior.
- Merge/publish/finalize semantics.
- Any `.p2p/` state edits.
