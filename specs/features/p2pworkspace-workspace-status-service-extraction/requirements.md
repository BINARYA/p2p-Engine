# P2PWorkspace Workspace Status Service Extraction Requirements

## Goal

Move basic workspace status, workspace health check, and proposal summary
scanning out of `P2PWorkspace` into a focused service.

## Requirements

- Add a `WorkspaceStatusService` that owns:
  - `ProposalSummary`;
  - `WorkspaceStatus`;
  - `WorkspaceCheck`;
  - project name/proposal status scan used by `status()`;
  - status-filtered proposal summaries;
  - required workspace file/directory check.
- `P2PWorkspace.status()`, `P2PWorkspace.proposal_summaries()`, and
  `P2PWorkspace.check()` must remain public compatibility facade methods.
- Preserve current project name fallback, proposal id parsing, title cleanup,
  proposal status parsing, and required-path check behavior.
- Remove filesystem helper functions that become unused after extraction.
- Do not move `ProposalDraftCommit` in this step.
- Do not edit `.p2p/` governance state by hand.

## Non-Goals

- Do not change proposal creation, update, contribution, decision, readiness, or
  branch behavior.
- Do not change CLI/MCP output shape.
- Do not change registry generation.
