# Execution Plan - PROP-092

This plan defines implementation verification boundaries for the proposal. It is not a detailed coding task list.

## Phase 1 - Command Surface Definition

Define the local MCP Work lifecycle tool set as domain-specific P2P operations:

- `p2p_work_branch`
- `p2p_work_submit`
- `p2p_work_review`
- `p2p_work_publish`
- `p2p_work_request_review`
- `p2p_work_accept`
- `p2p_work_finalize`
- `p2p_work_cleanup`

Existing read and planning tools remain part of the same surface:

- `p2p_work_list`
- `p2p_work_status`
- `p2p_work_show`
- `p2p_work_plan`

## Phase 2 - Permission And Consent Contract

Classify Work tools by risk:

- preparatory local operations: branch, submit, review;
- remote/external operations: publish, request-review;
- owner-controlled operations: accept, finalize, cleanup;
- destructive optional behavior: remote branch deletion during cleanup.

Privileged operations must validate a consent receipt before execution and consume or mark it with structured result metadata after execution.

## Phase 3 - Handler Reuse

Implement MCP handlers as thin adapters over existing Work lifecycle services or a shared command layer.

Handlers must not duplicate the Work state machine and must not call raw Git directly except through existing P2P services.

## Phase 4 - Failure Semantics

The implementation must fail closed on:

- wrong Work status;
- wrong current branch;
- dirty worktree;
- missing managed branch;
- missing remote;
- malformed Work manifest;
- consent operation mismatch;
- consent target mismatch;
- consent actor mismatch;
- expired or consumed consent;
- merge conflicts during accept.

Merge conflicts must return structured conflict output and must not trigger finalize or cleanup.

## Phase 5 - Documentation And Boundary

Documentation must state that these tools belong to the local/core MCP adapter.

Remote HTTP MCP, Wavekit authentication, hosted project grants, external MCP client sessions, OAuth, billing, tenant isolation, and rate limits are out of core scope.

## Acceptance Verification

The proposal is implementation-ready when:

- MCP catalog exposes the full local Work lifecycle surface.
- MCP registry tests prove the tool schemas are discoverable.
- MCP handler tests prove happy paths call the Work lifecycle services.
- Consent tests prove privileged operations reject missing, mismatched, expired, or already consumed receipts.
- Failure tests prove wrong state, wrong branch, dirty worktree, missing remote, and manifest errors fail closed.
- Accept tests prove merge conflicts return structured conflict payloads.
- Cleanup tests prove local and remote deletion flags are explicit and audited.
- Documentation distinguishes local MCP parity from Wavekit remote gateway responsibilities.
