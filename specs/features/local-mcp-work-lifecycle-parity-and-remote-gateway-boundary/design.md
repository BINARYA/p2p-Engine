# Design - Local MCP Work Lifecycle Parity And Remote Gateway Boundary

## Design Goals

This design implements `PROP-092` as local MCP parity over the existing managed
Work lifecycle.

The central design choice is to expose Work lifecycle operations through the
local MCP adapter without moving lifecycle logic into MCP. MCP catalog modules
describe the public tool surface, MCP handlers translate arguments and package
responses, and existing Work lifecycle services remain the source of state
transition behavior.

The second design choice is to separate remote transport concerns from this
feature. P2P Engine becomes local-MCP complete for Work operations; Wavekit or
another remote gateway remains responsible for remote HTTP MCP, authentication,
user grants, hosted-project isolation, and commercial policy.

## Relevant Existing Code

- `src/p2p_engine/services/work_branches.py` owns managed Work branch, submit,
  review, publish, request-review, accept, finalize, cleanup, and scan
  behavior.
- `src/p2p_engine/storage/filesystem.py` exposes `P2PWorkspace` facade methods
  such as `branch_work`, `submit_work`, `review_work`, `publish_work`,
  `request_external_work_review`, `accept_work`, `finalize_work`, and
  `cleanup_work`.
- `src/p2p_engine/services/consent.py` owns consent receipt grant, request,
  validate, consume, revoke, and error marking behavior.
- `src/p2p_engine/mcp/consent_audit.py` owns reusable consent/audit helpers
  for MCP operations that consume receipts and create audit commits.
- `src/p2p_engine/mcp/catalog/work_specs.py` currently exposes Work read and
  plan tools.
- `src/p2p_engine/mcp/handlers/work_specs.py` currently dispatches Work read
  and plan tools.
- `src/p2p_engine/mcp/catalog/collaboration.py` and
  `src/p2p_engine/mcp/handlers/collaboration_proposals.py` contain the existing
  permission-gated MCP proposal branch pattern.
- `tests/test_work_branch_service.py` covers Work lifecycle service behavior.
- `tests/test_cli.py` covers Work CLI public behavior.
- `tests/test_mcp.py`, `tests/test_mcp_registry.py`, and
  `tests/test_mcp_work_spec_handler.py` cover MCP public contracts.

## Decisions

### D001 - Keep Work Lifecycle In The Service Layer

New MCP tools call `P2PWorkspace` Work lifecycle facade methods, which delegate
to existing Work services.

Rationale:

- preserves the CLI as behavioral precedent;
- avoids a second state machine in MCP;
- keeps tests focused on service behavior where possible;
- matches current architecture where `P2PWorkspace` is a compatibility facade.

Covers: R002-R009, R018-R022, R038, N001-N002, N008.

### D002 - Add Work Tools To The Work MCP Catalog

Add new Work lifecycle tool definitions in `mcp/catalog/work_specs.py`, next to
the existing Work list/status/show/plan tools.

Initial tool set:

- `p2p_work_branch`
- `p2p_work_submit`
- `p2p_work_review`
- `p2p_work_publish`
- `p2p_work_request_review`
- `p2p_work_accept`
- `p2p_work_finalize`
- `p2p_work_cleanup`

Rationale:

- keeps Work tools grouped with Work/spec surfaces;
- avoids mixing Work lifecycle into proposal collaboration catalog code;
- makes registry tests straightforward.

Covers: R001-R009, R031-R032, AC001.

### D003 - Extend The Work MCP Handler

Extend `mcp/handlers/work_specs.py` for Work lifecycle dispatch.

The handler may delegate repeated consent/audit behavior to a small helper
module or helper functions if duplication grows beyond a few lines.

Rationale:

- keeps dispatch close to existing Work MCP tools;
- avoids registry-level domain logic;
- allows focused handler tests without changing CLI code.

Covers: R032-R034, N001, N007.

### D004 - Keep Preparatory Local Tools Consent-Free In The MVP

`p2p_work_branch`, `p2p_work_submit`, and `p2p_work_review` do not require
consent receipts in the first implementation.

Rationale:

- this matches the accepted local MCP parity direction;
- these operations remain local and preparatory;
- existing service preconditions already protect state, branch, and worktree
  correctness;
- privileged remote and owner-controlled steps remain consent-gated.

Covers: R010.

### D005 - Consent-Gate Privileged Work Tools

Consent-gated tools:

- `p2p_work_publish` uses operation `work_publish`;
- `p2p_work_request_review` uses operation `work_request_review`;
- `p2p_work_accept` uses operation `work_accept`;
- `p2p_work_finalize` uses operation `work_finalize`;
- `p2p_work_cleanup` uses operation `work_cleanup`.

Required input for these tools:

- `work_id`;
- `actor_id`;
- `consent_id`;
- operation-specific optional arguments.

Rationale:

- these operations publish remotely, request external review, merge, push base
  branches, or delete branches;
- the operations already exist in `CONSENT_OPERATIONS`;
- this matches the existing proposal branch MCP permission-gated pattern.

Covers: R005-R017, AC003-AC005.

### D006 - Reuse Consent Audit Helpers

Privileged Work MCP handlers should follow the existing pattern:

1. validate consent before the Work operation;
2. capture `safe_head` before execution when state-changing failure is possible;
3. call the Work lifecycle facade method;
4. consume consent with structured result metadata on success;
5. mark consent `used_with_error` for detected state-changing failures or
   merge conflicts;
6. commit and push consent audit metadata only through existing helper behavior.

If proposal-specific helper names become misleading, extract neutral helpers
without changing existing proposal behavior.

Covers: R016-R017, N007.

### D007 - Preserve Existing Work Error Semantics

MCP handlers should not reinterpret service errors into unrelated status codes
in the first implementation. Existing `ValueError` messages from Work services
remain the failure source unless a stable MCP error envelope already exists.

Rationale:

- keeps behavior aligned with CLI/service;
- avoids inventing a new domain error system in this feature;
- leaves future explicit domain error models as a separate improvement.

Covers: R018-R022, N004.

### D008 - Return Structured Success Payloads

Each MCP handler returns a stable JSON-ready payload:

```yaml
work_branch: ...
governance:
  owner_decision_required: false
  merge_performed: false
```

or, for consent-gated operations:

```yaml
work_publish: ...
consent: ...
governance:
  owner_decision_required: true
  merge_performed: false
  finalized: false
  cleanup_performed: false
```

Names should match the operation where practical:

- `work_branch`
- `work_submit`
- `work_review`
- `work_publish`
- `work_review_request`
- `work_accept`
- `work_accept_conflict`
- `work_finalize`
- `work_cleanup`

Covers: R023-R028, R033-R034.

### D009 - Preserve Accept Conflict Semantics

If `accept_work` returns `WorkAcceptConflict`, the MCP handler returns
structured conflict output and marks the consent receipt as used with error.

The response must include:

- conflicted Work id;
- source branch;
- base branch;
- conflicted files;
- consent state;
- governance metadata with `manual_resolution_required: true` and
  `merge_performed: false`.

Rationale:

- merge conflicts are a state-changing exceptional path;
- agents need machine-readable conflict information;
- finalize and cleanup must not happen after conflict.

Covers: R023-R024, AC005.

### D010 - Keep Finalize And Cleanup Separate

Finalize pushes the accepted base branch. Cleanup deletes local and optionally
remote Work branches after finalization.

The MCP implementation must not collapse these steps.

Rationale:

- current Work lifecycle keeps these actions separate;
- cleanup is more destructive than finalize;
- the owner must be able to stop between push and branch deletion.

Covers: R025-R028, AC006-AC007.

### D011 - Keep Provider PR/MR Automation Out

`p2p_work_request_review` records provider-advisory metadata only. It may return
suggested next steps from the existing service, but must not create GitHub PRs,
GitLab MRs, or provider-side records.

Rationale:

- provider PR/MR creation is a separate product adapter decision;
- current CLI behavior is advisory only;
- this feature is local MCP parity, not provider automation.

Covers: R029, AC008.

### D012 - Document Local And Remote Boundaries

Update MCP and/or development documentation to say:

- P2P Engine local MCP is CLI-parity oriented for local Work lifecycle tools;
- local parity does not imply unlimited remote authority;
- remote HTTP MCP, authenticated users, client grants, strong receipts, hosted
  audit, rate limits, tenancy, and billing belong outside the P2P core;
- Wavekit remote gateway should reuse the same core lifecycle rather than
  duplicating Work rules.

Covers: R035-R036, AC011.

## Tool Contract Sketch

### Preparatory Tools

```yaml
p2p_work_branch:
  required: [root, work_id]
  returns: [work_branch, governance]

p2p_work_submit:
  required: [root, work_id]
  returns: [work_submit, governance]

p2p_work_review:
  required: [root, work_id]
  returns: [work_review, governance]
```

### Consent-Gated Tools

```yaml
p2p_work_publish:
  required: [root, work_id, actor_id, consent_id]
  optional: [remote]
  consent_operation: work_publish

p2p_work_request_review:
  required: [root, work_id, actor_id, consent_id]
  optional: [provider]
  consent_operation: work_request_review

p2p_work_accept:
  required: [root, work_id, actor_id, consent_id]
  consent_operation: work_accept

p2p_work_finalize:
  required: [root, work_id, actor_id, consent_id]
  optional: [remote]
  consent_operation: work_finalize

p2p_work_cleanup:
  required: [root, work_id, actor_id, consent_id]
  optional: [delete_remote, remote]
  consent_operation: work_cleanup
```

## Handler Flow For Consent-Gated Tools

1. Read and require `work_id`, `actor_id`, and `consent_id`.
2. Validate consent with exact operation, target `work_id`, and actor.
3. Capture `safe_head` when the operation may change repository state.
4. Execute the matching Work lifecycle method on `P2PWorkspace`.
5. If the service returns a conflict object, mark consent used with error and
   return conflict metadata.
6. If the service raises after HEAD changes, mark consent used with error.
7. On success, consume consent with structured result metadata and audit commit.
8. Return JSON-ready result, consent, and governance/effect metadata.

## Testing Strategy

The implementation should follow `specs/skills/TEST_QUALITY_SKILL.md`:

- use `tests/test_work_branch_service.py` only for domain behavior changes;
- use `tests/test_mcp_registry.py` for tool schema and catalog contract;
- use `tests/test_mcp_work_spec_handler.py` for focused handler dispatch tests
  with fake workspace behavior where possible;
- use `tests/test_mcp.py` for public MCP integration payloads, permission
  boundaries, and failure contracts;
- use `tests/test_cli.py` only to prove existing CLI behavior remains
  compatible when touched;
- avoid duplicating every service lifecycle scenario at MCP level when the MCP
  layer only delegates.

Recommended focused validation during implementation:

```bash
.venv/bin/pytest tests/test_mcp_work_spec_handler.py tests/test_mcp_registry.py
.venv/bin/pytest tests/test_mcp.py
.venv/bin/pytest tests/test_work_branch_service.py
```

Recommended public and full validation before commit:

```bash
./scripts/test-public.sh
./scripts/test-full.sh
```

## Risks And Mitigations

### RSK001 - Duplicated Work Rules

Risk: MCP handlers reimplement Work state checks already owned by the service.

Mitigation: handlers only validate MCP arguments and consent, then delegate.

### RSK002 - Consent Audit Duplication

Risk: each Work handler copies large proposal-branch consent code.

Mitigation: reuse or extract neutral consent/audit helpers when repeated code
becomes non-trivial.

### RSK003 - Over-Testing At Public Layers

Risk: every service scenario is repeated in MCP integration tests.

Mitigation: test service behavior once, then test representative MCP contracts,
consent boundaries, and payload shapes.

### RSK004 - Remote Scope Creep

Risk: implementation introduces remote server or Wavekit identity concepts.

Mitigation: keep remote gateway references in docs only; do not add runtime
auth, users, OAuth, billing, or tenancy.

### RSK005 - Cleanup Destructiveness

Risk: remote branch deletion is hidden or implicit.

Mitigation: require explicit `delete_remote`, consent-gate cleanup, and assert
`remote_deleted` in tests.

## Compatibility

This feature is additive for MCP. Existing CLI commands and service behavior
must remain compatible. Existing Work MCP read/plan tools must remain
compatible. New tools may consume consent receipts and create audit commits
according to existing permission-gated MCP patterns.
