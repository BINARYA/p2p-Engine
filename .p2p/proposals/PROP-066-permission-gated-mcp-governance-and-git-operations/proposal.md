# PROP-066 - Permission-Gated MCP Governance And Git Operations

## Status

`accepted`

## Problem

The MCP surface intentionally excludes governance, ownership-sensitive, import, Git lifecycle, and repository publishing operations. These capabilities may become useful for advanced agent workflows, but exposing them before a repository permission and ownership model is defined would let agents perform actions that should remain owner-controlled.

## Context

Current MCP tools are limited to read-only, write-safe deterministic, and advisory prompt operations. Deferred operations include proposal accept/reject/defer, choice decide/block, conflict/vote/precedent record, spec import, Work publish/accept/finalize/cleanup, proposal branch publish/request-review/retire/accept/reject/merge, push/pull, merge, provider PR/MR workflows, and other repository-sensitive operations.

Recent concurrent collaboration work clarified that P2P should expose a safe MCP surface now, but privileged MCP operations must not rely on local actor names as strong identity. In a local or Git-only setup, actor IDs are declarative audit metadata. In cloud-backed repositories, the strongest enforcement comes from the Git provider: repository permissions, protected branches, required approvals, and token scopes. A future API server or IAM integration may add stronger identity verification, but it is not required for the first permission-gated MCP model.

## Goals

- Preserve the future requirement so missing MCP operations are not forgotten.
- Define a concrete permission model for privileged MCP operations.
- Use project-declared roles as the MVP authorization model while acknowledging they are not strong authentication.
- Require consent receipts for owner-controlled MCP operations.
- Keep Git provider enforcement as the cloud-backed security boundary for protected branches and main updates.
- Support generic fallback identities when project init does not know real person names.
- Keep future API server/IAM integration possible without blocking the MVP.

## Non-Goals

- Implement privileged MCP methods before this proposal is accepted.
- Treat local actor_id values as strong authentication.
- Require an external IAM server for the MVP.
- Allow agents to bypass owner governance decisions.
- Expose Git commit, push, merge, provider PR/MR creation, or finalization without accepted permission and consent rules.

## Proposal

Adopt a hybrid Role + Consent Receipt model for permission-gated MCP governance and Git operations.

P2P distinguishes three concepts:

- actor_id: the declared person, agent, or client performing work; useful for audit and collaboration but not strong authentication in local/Git-only mode.
- authorizer: the project role or owner identity that approves a privileged operation.
- enforcer: the mechanism that actually prevents unauthorized state changes. In local projects this is mostly P2P policy and audit. In cloud-backed projects this must be Git provider permissions, branch protection, required approvals, and token scopes.

Project-declared roles are stored in versioned P2P project policy, such as `.p2p/project/permissions.yml` or an equivalent generated policy file. On project init, P2P should ask for or accept an owner display name. If no owner is provided, it creates a generic `owner` identity. Contributor identities may be added later; if no contributor name is known, P2P may use generic `contributor` or agent IDs for branch metadata.

Example policy:

```yaml
permissions:
  version: 1
  identities:
    owner:
      role: owner
      kind: person
      display_name: owner
    contributor:
      role: contributor
      kind: person
      display_name: contributor
  roles:
    owner:
      can_grant_consent: true
      can_manage_permissions: true
    maintainer:
      can_request_privileged_operations: true
    contributor:
      can_create_local_branches: true
      can_request_review: true
    agent:
      can_use_safe_tools: true
    readonly:
      can_read: true
```

Tool classes:

- safe_read: read/status/context/scan tools; no consent required.
- write_safe_preparatory: deterministic or local preparatory operations such as fetch and proposal branch creation; no owner consent required by default, but must be audited when they touch Git state.
- privileged_publish: publish, push, request-review, provider PR/MR handoff; requires a valid consent receipt unless project policy explicitly allows the actor role.
- owner_controlled_governance: accept, reject, defer, choice decide, select candidate, merge, finalize, cleanup; requires owner consent receipt.
- destructive_or_external: cleanup, branch deletion, provider side effects, irreversible remote changes; requires owner consent receipt, single-use, and explicit audit.

Consent receipts are versioned audit records granting one bounded privileged operation. They include consent_id, operation, target, actor_id, requested_by, approved_by, role, scope, expiry, single_use flag, created_at, and optional provider metadata. Sensitive MCP tools must refuse execution without a valid unexpired receipt. After single-use execution, the receipt is marked consumed with result metadata.

The MVP does not require external IAM. Project init should support an owner name but must fall back to generic `owner`. The model is declarative and auditable locally. In cloud-backed projects, robust enforcement depends on Git provider controls protecting main and privileged remote actions. A future P2P API server may replace or augment declarative identities with authenticated users, OAuth, organization membership, signed consent, or IAM-backed policy checks.

Safe MCP surface may remain available before privileged consent implementation: sync status/fetch and proposal branch/status/scan. MCP pull, push, publish, request-review, retire, accept, reject, merge, finalize, cleanup, provider PR/MR handoff, and protected-branch updates remain deferred until role policy, consent receipts, and audit records are implemented.

## Acceptance Criteria

- The proposal defines project-declared roles for owner, maintainer, contributor, agent, and readonly.
- The proposal specifies owner-name capture during project init and generic fallback identities such as owner and contributor.
- The proposal distinguishes actor_id, authorizer, and enforcer.
- The proposal states that local actor IDs are audit metadata, not strong authentication.
- The proposal states that cloud enforcement relies on Git provider permissions, branch protection, required approvals, and token scopes.
- The proposal defines tool classes: safe_read, write_safe_preparatory, privileged_publish, owner_controlled_governance, and destructive_or_external.
- The proposal requires consent receipts for privileged MCP operations and defines required receipt fields.
- The proposal requires single-use consent for merge, finalize, cleanup, destructive, or protected-branch operations.
- The proposal allows the safe MCP surface to remain available before privileged MCP implementation.
- The proposal defers external IAM/API-server authentication to a future enhancement while preserving compatibility.

## Decision

Pending.
