# P2PWorkspace Proposal Draft Commit Service Extraction Requirements

## Goal

Move proposal draft commit behavior and its result type out of `P2PWorkspace`
into a focused service.

## Requirements

- Add a service that owns `ProposalDraftCommit`.
- Preserve existing `commit_proposal_draft(proposal_id, actor)` behavior:
  - verify the proposal exists;
  - require a Git repository;
  - reject detached HEAD;
  - require uncommitted changes;
  - commit all changes with the existing message format;
  - return proposal id, commit hash, and changed files.
- Keep `P2PWorkspace.commit_proposal_draft()` as the public compatibility facade.
- Preserve MCP output for `p2p_proposal_draft_commit`.
- Do not change proposal branch lifecycle behavior.
- Do not edit `.p2p/` governance state by hand.

## Non-Goals

- Do not change raw Git helper functions.
- Do not change managed proposal branch behavior.
- Do not introduce partial-file commits.
- Do not alter commit message format.
