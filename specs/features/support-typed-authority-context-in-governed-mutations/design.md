# Design - Support Typed Authority Context In Governed Mutations

## Requirements Covered

- R001-R040
- N001-N006
- AC001-AC010

## Decision Summary

P2P Engine gains one versioned authority vocabulary without becoming a hosted
authorization service. A project stores a stable authority descriptor. Each
integrated governed write carries an `AuthorityContext` resolved either by
local P2P policy or attested by an external provider. The normalized context is
part of preview, apply, receipt and audit identity. Proposal decisions are the
first complete delegated flow; later domain and structure features consume the
same contract.

## Key Decisions

### D001 - Authority, Subject And Executor Are Different Identities

The project authority descriptor identifies the accountable authority root.
The authorized subject identifies whose capability permits the mutation. The
executor identifies the user-controlled client or agent that initiated it.
The worker is transport infrastructure and is never recorded as the human or
agent initiator merely because it launched the CLI process.

### D002 - External Attestation Is Recorded Evidence, Not Remote Verification

P2P validates shape, capability, descriptor binding and semantic consistency.
It does not call WaveKit, inspect PostgreSQL or claim that the external grant is
currently valid. The trusted hosted boundary must authenticate and authorize
before constructing the context and must protect its worker invocation path.

### D003 - No Hosted Grant Mirror In Project Memory

The workspace stores the authority descriptor and immutable evidence attached
to performed operations, not a mutable copy of current memberships or grants.
This avoids split-brain authorization state and allows project memory to explain
who authorized a historical operation after a grant is revoked.

### D004 - Capability Names Belong To Governed P2P Operations

P2P owns stable names only for mutations it performs. Provider-only actions
such as inviting members, managing grants or deleting a hosted project remain
outside the P2P registry. The provider decides which P2P capabilities may be
delegated; P2P declares operation semantics and local-policy requirements.

### D005 - Authority Evidence Is A Semantic Mutation Input

The canonical context digest is included in preview tokens, idempotency
fingerprints, transaction evidence, receipts and mutation events. A changed
grant generation or executor is a changed request, not a retry. Once a receipt
proves apply, recovery returns that immutable result and does not ask whether
the grant is still active.

### D006 - Proposal Decisions Prove The Abstraction First

The existing decision lifecycle already separates actor and executor and uses
preview/apply receipts. It becomes the first end-to-end consumer. Normal
decisions require `proposal.decide`; readiness override additionally requires
`proposal.readiness.override` with root-authority basis in external policy v1.
This closes the real delegated-decision use case before broadening integration.

### D007 - Schema 4 Uses Neutral Authority Identity

Hosted authority identifiers use neutral opaque semantics such as
`wk-project-authority-<opaque-id>`, never a mutable owner's identity. Schema 4
does not retain a compatibility interpretation for `wk-owner-*`; development
workspaces are recreated or explicitly migrated by a separate approved tool.

### D008 - Initialization Bootstraps Rather Than Looks Up Authority

Before initialization there is no current descriptor to compare. Local init
creates a local-policy root; hosted init supplies the candidate external root
and root-authority attestation in one bootstrap context. Candidate descriptor,
project state and initialization receipt commit atomically. Every later write
must match the persisted descriptor and generation.

### D009 - Authority Generation Changes Through A Receipt

Hosted ownership transfer cannot update only PostgreSQL once P2P validates the
descriptor generation. P2P therefore provides `project.authority.rotate`,
authorized by the current root and bound to previous/new descriptors. It
atomically advances the descriptor generation with event and receipt. The
provider then finalizes its owner state from that receipt; uncertain outcomes
use status/replay instead of guessing.

## Contract Sketch

Illustrative external context, with exact field names finalized by contract
tests:

```json
{
  "schema": "p2p-authority-context/v1",
  "mode": "external_attestation",
  "project_authority": {
    "id": "wk-project-authority-R7K3...",
    "generation": 2,
    "provider": "wavekit",
    "policy_version": "wavekit-project-capabilities/v1"
  },
  "subject": {
    "id": "wk-project-actor-A91...",
    "kind": "user"
  },
  "executor": {
    "id": "wk-project-client-C52...",
    "kind": "mcp_client"
  },
  "authorization_decision_id": "wk-authz-D44...",
  "authorized_at": "2026-08-25T12:00:00Z",
  "claims": [
    {
      "capability": "proposal.decide",
      "basis": "capability_grant",
      "grant_ref": "wk-grant-G18...",
      "grant_generation": 1
    }
  ]
}
```

The serialized contract is accepted through a typed input boundary, preferably
an allowlisted JSON file or stdin channel for server use. Shell-expanded JSON,
raw environment secrets and arbitrary provider payloads are rejected.

## Capability Matrix

| Feature | Governed operation | P2P capability | Initial hosted delegation |
|---|---|---|---|
| `separate-domain-from-structure-source` | initialize project | `project.initialize` | root only |
| authority lifecycle | rotate authority generation | `project.authority.rotate` | root only |
| `separate-domain-from-structure-source` | set/clear domain | `project.domain.change` | root only |
| `introduce-project-owned-structure` | add/update/reorder structure | `project.structure.edit` | root only |
| `classify-project-memory-against-structure` | assign memory scope | `project.memory.classify` | root only |
| proposal decision lifecycle | decide proposal | `proposal.decide` | delegable |
| proposal decision lifecycle | override readiness gate | `proposal.readiness.override` | root only |
| `retire-structure-elements-with-impact-resolution` | retire structure | `project.structure.retire` | root only |
| `export-project-structure-as-vertical` | export structure | `project.vertical.export` | root only |
| `replace-project-structure-from-release` | replace structure | `project.structure.replace` | root only |
| `merge-and-restore-project-structure` | merge structure | `project.structure.merge` | root only |
| `merge-and-restore-project-structure` | restore structure | `project.structure.restore` | root only |
| `rebase-readiness-on-project-structure` | read readiness | none, read-only | transport policy |

"Root only" is the initial external-provider policy expectation, not a local
WaveKit role embedded in P2P code. The coordinated feature specifications name
the capability and defer provider delegability to provider policy.

## Components And Ownership

- Authority descriptor and context domain models with strict serializers.
- Authority bootstrap/rotation service with receipt and recovery integration.
- Governed-capability registry owned by the project-domain layer.
- Local-policy resolver adapter over existing P2P actor/permission services.
- External-attestation structural validator with no network client.
- Authority digest and audit-safe receipt/event projection helpers.
- Proposal decision service, CLI and MCP integration.
- Workspace validator, snapshot/status serializers and documentation generator.

## Proposal Decision Flow

```text
caller resolves local policy or external provider authorization
-> decision preview receives typed AuthorityContext
-> P2P validates descriptor, claims, actor/executor and decision preconditions
-> preview token binds decision inputs plus authority digest
-> apply resubmits exact context, token and operation key
-> atomic decision event and receipt record subject, executor and evidence
-> replay/status returns the immutable outcome without re-authorizing
```

For external mode, "validates" means validates the declared contract and its
binding to this project and operation. It never means that P2P queried the
external provider.

## Failure And Recovery Semantics

- Validation or capability mismatch fails before transaction start.
- Stale project authority generation invalidates preview/apply.
- A changed external grant generation produces operation-key conflict when the
  key was previously used with another context.
- If apply status is unknown, receipt/transaction recovery is consulted first.
- A proven applied mutation is reconciled even if the provider later revokes
  the grant; a mutation not started must be authorized anew by the provider.

## Alternatives Considered

- Mirror WaveKit grants into `.p2p`: rejected because two mutable authorization
  sources can diverge and standalone P2P does not need hosted memberships.
- Pass only an owner actor string: rejected because it erases delegation and
  lets a worker impersonate a stable owner identity.
- Let P2P call the provider during apply: rejected because it breaks offline
  operation, introduces availability coupling and crosses the product boundary.
- Use OAuth scopes as project capabilities: rejected because OAuth limits a
  client, while project grants authorize a subject inside one project.
- Add multiple owners now: rejected because accountability, transfer,
  revocation and concurrent-decision semantics require a separate design.

## Migration And Compatibility

This is a schema-4 and P2P 0.5.0 contract. There is no runtime fallback to the
0.4.x stable-owner encoding. Fixtures, bundled examples, generated templates
and WaveKit integration are regenerated from one immutable release candidate.
