# P2PWorkspace Proposal Draft Commit Service Extraction Tasks

## Phase 1: Audit

- [x] T001 Confirm `ProposalDraftCommit` is the last dataclass in
      `storage.filesystem`.
- [x] T002 Confirm `commit_proposal_draft()` is the only behavior using it.
- [x] T003 Confirm MCP calls the public workspace facade.

## Phase 2: Service Extraction

- [x] T004 Add `services.proposal_drafts` with `ProposalDraftCommit`.
- [x] T005 Implement `ProposalDraftCommitService.commit()`.
- [x] T006 Wire the service into `P2PWorkspace`.
- [x] T007 Delegate `P2PWorkspace.commit_proposal_draft()` to the service.
- [x] T008 Remove `ProposalDraftCommit` from `storage.filesystem`.
- [x] T009 Confirm no dataclasses remain in `storage.filesystem`.

## Phase 3: Verification

- [x] T010 Add focused service tests for success and validation errors.
- [x] T011 Run focused service and MCP draft commit tests.
- [x] T012 Run `p2p validate`.
- [x] T013 Run the full pytest suite.
- [x] T014 Update the refactoring status tracker.
