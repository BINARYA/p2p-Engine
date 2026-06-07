# P2PWorkspace Workspace Status Service Extraction Design

## Current State

`P2PWorkspace` still directly implements:

- `status()`;
- `proposal_summaries()`;
- `check()`;
- `ProposalSummary`, `WorkspaceStatus`, and `WorkspaceCheck`.

Those operations are read-only workspace inspection behavior and do not need to
live in the storage facade.

## Target State

Create `p2p_engine.services.workspace_status` with:

- dataclasses for the three workspace status result models;
- project/proposal scanning helpers;
- required-path validation for workspace bootstrap checks.

`P2PWorkspace` gets a lazy `_workspace_status_service()` and delegates the
public methods to it.

## Compatibility

The new service preserves existing behavior:

- project name defaults to `Unknown`;
- proposal ids are derived from the first two `-` separated directory parts;
- proposal status is read from `## Status \`...\`` in `proposal.md`;
- proposal titles strip the leading proposal id;
- `check()` returns relative paths for missing required artifacts.

## Verification

Add focused service tests plus facade regression, then run focused CLI/MCP tests,
`p2p validate`, and the full pytest suite.
