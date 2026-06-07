# P2PWorkspace Proposal Draft Commit Service Extraction Design

## Current State

`P2PWorkspace.commit_proposal_draft()` directly performs Git checks and creates
the draft commit. It is now the only dataclass-backed behavior left in
`storage.filesystem`.

## Target State

Add `services.proposal_drafts` with:

- `ProposalDraftCommit`;
- `ProposalDraftCommitService.commit()`.

The service receives injected dependencies for:

- proposal directory lookup;
- Git status;
- changed-file listing;
- commit creation;
- actor identity normalization.

`P2PWorkspace` wires those dependencies and delegates the public method.

## Compatibility

The extraction preserves current errors and output fields. The service remains
small because this behavior is an escape hatch for committing raw proposal draft
changes, while managed branch lifecycle remains in `ProposalBranchService`.

## Verification

Add direct service tests for success and validation failures, keep MCP coverage,
then run `p2p validate` and the full suite.
