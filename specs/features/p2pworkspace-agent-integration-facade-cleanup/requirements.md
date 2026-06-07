# P2PWorkspace Agent Integration Facade Cleanup Requirements

## Goal

Remove private `P2PWorkspace` wrapper methods that only forward agent
integration registry behavior to `AgentInstructionService`.

## Requirements

- Public workspace methods for agent integrations must keep the same behavior.
- `ValidationService` must depend on the agent instruction service path provider
  directly instead of a private `P2PWorkspace` wrapper.
- No `.p2p/` governance state may be edited by hand.
- No CLI, MCP, or validation command behavior may change.
- Tests must cover agent integration service behavior and validation behavior.

## Non-Goals

- Do not change agent instruction file templates.
- Do not change the registry schema.
- Do not change installation, uninstall, drift, or force-update semantics.
