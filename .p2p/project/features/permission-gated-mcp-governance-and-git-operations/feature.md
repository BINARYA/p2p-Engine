# Permission-Gated MCP Governance And Git Operations

## Provenance

- Proposal: PROP-066
- Source: .p2p/proposals/PROP-066-permission-gated-mcp-governance-and-git-operations

## Problem

The MCP surface intentionally excludes governance, ownership-sensitive, import, Git lifecycle, and repository publishing operations. These capabilities may become useful for advanced agent workflows, but exposing them before a repository permission and ownership model is defined would let agents perform actions that should remain owner-controlled.

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

## Decision

# Decision - PROP-066

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Accepted as the permission-gated MCP model: project-declared roles, owner/contributor fallback identities, consent receipts for privileged operations, audit records, and Git provider enforcement for cloud-backed repositories.

## Date

2026-06-02

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-41d214f07fc04f5872539575

## Decision Fingerprint

70cd014fc145bfa64fb696e3efe7eabf4633ee546207b0f4ef71661747431d90

## Lineage

None.

## Canonical Source

decision-events.yml
