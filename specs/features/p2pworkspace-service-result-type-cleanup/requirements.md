# P2PWorkspace Service Result Type Cleanup Requirements

## Goal

Remove duplicated result dataclasses from `storage.filesystem` when the same
types are already owned and constructed by extracted services.

## Requirements

- `P2PWorkspace` must import service-owned result types for:
  - project state status and project brief prompt;
  - project assessment;
  - registry status and registry view;
  - software spec status and prompt;
  - software spec export status and validation;
  - remote project profile.
- Public `P2PWorkspace` method names, return attributes, CLI output, MCP output,
  and test-visible behavior must remain unchanged.
- The cleanup must not touch proposal/readiness/permission/consent models unless
  their ownership is reassessed in a separate step.
- No `.p2p/` governance state may be edited by hand.

## Non-Goals

- Do not change service behavior.
- Do not change generated artifacts or validation rules.
- Do not remove facade methods.
- Do not rename public result attributes.
