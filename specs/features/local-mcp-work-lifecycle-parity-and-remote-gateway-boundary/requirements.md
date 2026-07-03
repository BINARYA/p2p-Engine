# Requirements - Local MCP Work Lifecycle Parity And Remote Gateway Boundary

## Origin And Scope

Source proposal: `PROP-092 - Local MCP Work Lifecycle Parity And Remote Gateway Boundary`.

This feature translates the accepted direction into local implementation
requirements for the runtime codebase. It is a development spec only. It does
not mutate P2P governance state and does not replace the accepted proposal.

The feature covers:

- local MCP parity for the existing managed Work lifecycle;
- domain-specific Work MCP tools instead of raw Git tools;
- consent-gated and state-gated handling for privileged Work operations;
- structured MCP responses for Work lifecycle effects, consent, governance,
  and merge conflicts;
- documentation that separates local MCP parity from remote Wavekit gateway
  responsibilities.

Out of scope for this feature:

- remote HTTP MCP server behavior;
- OAuth, client registration, Wavekit login, hosted tenancy, billing, global
  rate limits, or hosted-project abuse controls;
- provider PR/MR creation;
- raw Git MCP tools;
- changing the existing Work CLI lifecycle semantics;
- changing the owner-controlled governance model.

## Assumptions

- The existing CLI Work lifecycle is the behavioral baseline.
- Existing `WorkBranchService` and `P2PWorkspace` facade methods remain the
  domain source for Work transitions.
- Existing proposal-branch MCP permission-gated handlers provide the preferred
  consent/audit implementation pattern.
- Existing consent operations already include Work operations for publish,
  request-review, accept, finalize, and cleanup.
- Local MCP operates in the caller's local execution context but must not imply
  unlimited authority over a canonical remote repository.

## Functional Requirements

### R001 - Preserve Existing Read Work MCP Surface

THE SYSTEM SHALL preserve existing MCP tools `p2p_work_list`,
`p2p_work_status`, `p2p_work_show`, and `p2p_work_plan` with backward-compatible
schemas and payloads unless this feature explicitly adds optional fields.

### R002 - Work Branch MCP Tool

WHEN `p2p_work_branch` is invoked with a valid `work_id`, THE SYSTEM SHALL
create and check out the managed Work branch by delegating to the existing Work
branch lifecycle behavior.

### R003 - Work Submit MCP Tool

WHEN `p2p_work_submit` is invoked with a valid `work_id`, THE SYSTEM SHALL
submit the current managed Work branch by delegating to the existing Work
submit lifecycle behavior.

### R004 - Work Review MCP Tool

WHEN `p2p_work_review` is invoked with a valid `work_id`, THE SYSTEM SHALL
record local owner review request metadata by delegating to the existing Work
review lifecycle behavior.

### R005 - Work Publish MCP Tool

WHEN `p2p_work_publish` is invoked with valid `work_id`, `actor_id`,
`consent_id`, and optional `remote`, THE SYSTEM SHALL publish the reviewed
managed Work branch only after validating a matching `work_publish` consent
receipt.

### R006 - Work Request Review MCP Tool

WHEN `p2p_work_request_review` is invoked with valid `work_id`, `actor_id`,
`consent_id`, and optional `provider`, THE SYSTEM SHALL record provider
advisory review handoff metadata only after validating a matching
`work_request_review` consent receipt.

### R007 - Work Accept MCP Tool

WHEN `p2p_work_accept` is invoked with valid `work_id`, `actor_id`, and
`consent_id`, THE SYSTEM SHALL accept the published managed Work branch by
delegating to the existing Work accept lifecycle behavior only after validating
a matching `work_accept` consent receipt.

### R008 - Work Finalize MCP Tool

WHEN `p2p_work_finalize` is invoked with valid `work_id`, `actor_id`,
`consent_id`, and optional `remote`, THE SYSTEM SHALL finalize the accepted
Work by pushing the base branch only after validating a matching
`work_finalize` consent receipt.

### R009 - Work Cleanup MCP Tool

WHEN `p2p_work_cleanup` is invoked with valid `work_id`, `actor_id`,
`consent_id`, optional `remote`, and optional `delete_remote`, THE SYSTEM SHALL
clean up the finalized managed Work branch only after validating a matching
`work_cleanup` consent receipt.

### R010 - Preparatory Tool Classification

THE SYSTEM SHALL classify `p2p_work_branch`, `p2p_work_submit`, and
`p2p_work_review` as local preparatory lifecycle tools that do not require a
consent receipt in the first implementation, while still relying on existing
Work state and Git preconditions.

### R011 - Privileged Tool Consent Validation

IF a privileged Work MCP tool is invoked without a granted matching consent
receipt, THEN THE SYSTEM SHALL fail before executing the Work lifecycle action.

### R012 - Consent Operation Match

IF the consent receipt operation does not match the requested Work MCP
operation, THEN THE SYSTEM SHALL reject the invocation and SHALL NOT execute
the Work lifecycle action.

### R013 - Consent Target Match

IF the consent receipt target does not match the requested `work_id`, THEN THE
SYSTEM SHALL reject the invocation and SHALL NOT execute the Work lifecycle
action.

### R014 - Consent Actor Match

IF the consent receipt actor does not match the requested `actor_id`, THEN THE
SYSTEM SHALL reject the invocation and SHALL NOT execute the Work lifecycle
action.

### R015 - Consent Status And Expiry

IF the consent receipt is requested, revoked, consumed, used with error, or
expired, THEN THE SYSTEM SHALL reject the invocation and SHALL NOT execute the
Work lifecycle action.

### R016 - Consent Consumption On Success

WHEN a privileged Work MCP operation succeeds, THE SYSTEM SHALL consume the
receipt and record structured result metadata for the operation.

### R017 - Consent Used With Error On State-Changing Failure

IF a privileged Work MCP operation changes repository state before failing,
THEN THE SYSTEM SHALL mark the consent receipt `used_with_error` with structured
failure metadata when the state change can be detected.

### R018 - Work State Preconditions

THE SYSTEM SHALL preserve existing Work lifecycle state preconditions for every
MCP tool, including planned before branch, branched before submit, submitted
before review, review_requested before publish, published before request-review
and accept, accepted before finalize, and finalized before cleanup.

### R019 - Branch Preconditions

THE SYSTEM SHALL preserve existing current-branch, base-branch, and managed
branch preconditions for Work lifecycle operations.

### R020 - Clean Worktree Preconditions

THE SYSTEM SHALL preserve existing clean-worktree preconditions for Work
operations that require a clean repository state.

### R021 - Remote Preconditions

THE SYSTEM SHALL preserve existing remote lookup and remote URL preconditions
for Work publish, request-review, finalize, and cleanup.

### R022 - Manifest Validation

IF a Work manifest is malformed or missing required Git metadata, THEN THE
SYSTEM SHALL reject the MCP invocation with the same domain error semantics as
the existing Work service.

### R023 - Accept Merge Conflict Payload

IF `p2p_work_accept` encounters merge conflicts, THEN THE SYSTEM SHALL return a
structured conflict payload and SHALL NOT report `merge_performed: true`,
finalize the Work, or clean up branches.

### R024 - Accept Success Payload

WHEN `p2p_work_accept` succeeds without conflicts, THE SYSTEM SHALL return the
Work accept result, consumed consent, and governance metadata indicating that
the merge was performed and finalization remains separate.

### R025 - Finalize Separation

THE SYSTEM SHALL NOT finalize a Work item as a side effect of branch, submit,
review, publish, request-review, or accept MCP operations.

### R026 - Cleanup Separation

THE SYSTEM SHALL NOT clean up local or remote managed Work branches as a side
effect of branch, submit, review, publish, request-review, accept, or finalize
MCP operations.

### R027 - Cleanup Remote Deletion Explicitness

WHEN `p2p_work_cleanup` is invoked, remote branch deletion SHALL occur only
when `delete_remote` is explicitly true.

### R028 - Cleanup Result Metadata

WHEN `p2p_work_cleanup` completes, THE SYSTEM SHALL return `local_deleted` and
`remote_deleted` result metadata.

### R029 - Provider Review Handoff Boundary

WHEN `p2p_work_request_review` completes, THE SYSTEM SHALL report advisory
review handoff metadata and SHALL NOT create GitHub pull requests, GitLab merge
requests, or provider-side review objects.

### R030 - No Raw Git MCP Tools

THE SYSTEM SHALL NOT add MCP tools for arbitrary raw Git push, merge, reset,
clean, force-push, checkout, or branch deletion as part of this feature.

### R031 - MCP Catalog Schemas

THE SYSTEM SHALL expose strict MCP tool schemas for each new Work lifecycle
tool with required fields matching the operation risk.

### R032 - MCP Handler Dispatch

THE SYSTEM SHALL dispatch each new Work MCP tool through the existing MCP
handler registry without adding unrelated domain logic to the registry.

### R033 - Structured Response Contract

THE SYSTEM SHALL return JSON-serializable MCP payloads with stable top-level
keys for result object, consent where applicable, and governance/effect
metadata.

### R034 - Mutation Evidence

WHEN a Work MCP tool mutates Work or Git state, THE SYSTEM SHALL return
structured evidence of the mutation or of the blocked/failed condition.

### R035 - Local MCP Boundary Documentation

THE SYSTEM SHALL document that these Work tools belong to the local/core MCP
adapter and do not implement remote multi-user Wavekit MCP.

### R036 - Remote Gateway Boundary Documentation

THE SYSTEM SHALL document that remote HTTP MCP, authentication, grants, strong
server-side receipt issuance, audit retention, rate limits, hosted tenancy, and
billing belong to Wavekit or another remote gateway layer.

### R037 - Existing CLI Compatibility

THE SYSTEM SHALL preserve existing `p2p work ...` CLI behavior and output unless
this feature explicitly adds backward-compatible documentation or examples.

### R038 - Existing Work Service Compatibility

THE SYSTEM SHALL preserve existing `WorkBranchService` behavior unless a change
is explicitly required to expose the same behavior through MCP.

## Non-Functional Requirements

### N001 - Adapter Thinness

MCP handlers SHALL remain thin adapters over `P2PWorkspace` or service-owned
Work lifecycle behavior.

### N002 - No State Machine Duplication

THE SYSTEM SHALL NOT duplicate the Work lifecycle state machine in MCP catalog
or handler code.

### N003 - Public Contract Stability

New MCP tool names, required fields, response keys, consent operations, and
governance metadata SHALL be stable enough for agent clients to consume.

### N004 - Fail Closed

Permission, consent, manifest, branch, worktree, remote, and Work state errors
SHALL fail closed before unsafe side effects whenever possible.

### N005 - Test Layer Discipline

Tests SHALL be added at the lowest useful layer and SHALL add MCP public-surface
coverage only where tool schema, payload, permission, or error contracts are
part of the behavior.

### N006 - No Remote Scope Creep

The implementation SHALL NOT introduce remote server, OAuth, Wavekit identity,
tenant, billing, or hosted collaboration infrastructure.

### N007 - Maintainability

The implementation SHALL prefer small reusable helpers for repeated
consent/audit handler patterns over copy-pasting large handler blocks.

### N008 - Compatibility Facade

`P2PWorkspace` MAY receive thin facade delegations or existing method reuse but
SHALL NOT become the owner of new Work lifecycle classification logic.

## Edge Cases And Errors

- Missing `work_id`.
- Unknown `work_id`.
- Wrong Work status for requested transition.
- Dirty worktree where clean state is required.
- Detached HEAD or wrong current branch.
- Missing managed branch.
- Missing remote or remote URL.
- Malformed Work manifest or missing `git` mapping.
- Consent receipt missing, requested, revoked, consumed, expired, or mismatched.
- Accept merge conflict.
- Cleanup requested with `delete_remote: false`.
- Cleanup requested with `delete_remote: true`.
- Provider value outside `generic`, `github`, or `gitlab`.

## Acceptance Criteria

- AC001: MCP registry exposes every new Work lifecycle tool with expected names,
  required arguments, and strict schemas.
- AC002: MCP handlers execute branch, submit, and review through existing Work
  lifecycle methods without requiring consent.
- AC003: MCP handlers reject privileged Work operations before execution when
  consent is missing or mismatched.
- AC004: MCP handlers consume consent receipts with structured result metadata
  when publish, request-review, accept, finalize, or cleanup succeeds.
- AC005: MCP accept returns structured conflict payload and marks consent
  consistently when a merge conflict occurs.
- AC006: MCP finalize never performs cleanup.
- AC007: MCP cleanup distinguishes local and remote deletion in both input and
  output.
- AC008: MCP request-review records provider advisory handoff and does not open
  external PR/MR objects.
- AC009: No raw Git MCP tools are added.
- AC010: Existing Work CLI and service tests remain compatible.
- AC011: Documentation clearly separates local MCP parity from remote Wavekit
  gateway responsibilities.
- AC012: Focused, public MCP, and full-suite validation evidence is available
  before commit.
