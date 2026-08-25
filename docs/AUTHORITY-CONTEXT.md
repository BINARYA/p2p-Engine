# Project Authority And Governed Mutations

Workspace schema 4 separates three identities:

- **project authority**: the accountable authority root for the project;
- **subject**: the person or agent whose capability authorizes one mutation;
- **executor**: the user-controlled client or agent that initiated it.

The process that invokes P2P is transport infrastructure. A hosted worker must
not replace the initiating subject or executor in project evidence.

## Authority Modes

Every project has `.p2p/project/authority.yml` with one current descriptor.

- `local_policy`: P2P resolves the subject and executor through
  `.p2p/project/permissions.yml`. Existing standalone owner workflows require
  no extra option.
- `external_attestation`: a trusted provider supplies a bounded, typed
  `p2p-authority-context/v1` JSON document. P2P validates and records the claim
  but does not call the provider or independently prove that a hosted grant is
  current.

Inspect the current descriptor and capability registry:

```bash
p2p project authority show --format json
p2p project authority capabilities --format json
```

Registry entries distinguish `implemented`, `planned` and
`existing_unintegrated` mutation surfaces. Only implemented external surfaces
may consume an external attestation.

Schema 4 is current-only. It has no 0.4.x authority compatibility branch and
does not reinterpret legacy owner-shaped hosted identifiers. Development
workspaces with older authority state must be recreated or migrated by a
separately approved, explicit tool.

## External Context

A context contains only bounded, audit-safe identifiers and exact claims:

```json
{
  "schema": "p2p-authority-context/v1",
  "mode": "external_attestation",
  "project_authority": {
    "id": "project-authority-42",
    "generation": 1,
    "provider_id": "hosted-provider",
    "provider_policy_version": "project-capabilities-v1"
  },
  "subject": {"id": "project-user-42", "kind": "user"},
  "executor": {"id": "mcp-client-7", "kind": "mcp_client"},
  "authorization_decision_id": "authz-decision-42",
  "authorized_at": "2026-08-25T15:00:00Z",
  "claims": [{
    "capability": "proposal.decide",
    "basis": "capability_grant",
    "grant_ref": "grant-42",
    "grant_generation": 3
  }]
}
```

Unknown fields, duplicate JSON keys, secret-like identifiers, stale authority
generations, a mode/provider mismatch or a non-exact capability set fail before
the mutation begins. Do not put access tokens, cookies, JWTs, database IDs or
provider payloads in this contract.

Use the same context for decision preview and apply:

```bash
p2p decision preview PROP-001 \
  --event-type accepted \
  --reason "Approved by the delegated decision capability." \
  --actor project-user-42 \
  --executor-actor mcp-client-7 \
  --executor-kind mcp_client \
  --authority-context authority-context.json \
  --format json

p2p decision apply PROP-001 \
  --event-type accepted \
  --reason "Approved by the delegated decision capability." \
  --actor project-user-42 \
  --executor-actor mcp-client-7 \
  --executor-kind mcp_client \
  --decided-on 2026-08-25 \
  --operation-key P2POP-... \
  --preview-token ... \
  --authority-context authority-context.json \
  --confirm --format json
```

An acceptance that uses `--override-readiness` additionally requires the exact
`proposal.readiness.override` claim with `root_authority` basis. A delegated
decision claim cannot grant that override by implication.

## Idempotency And Audit

The canonical context digest is bound to the preview token, request
fingerprint, decision event and mutation receipt. Changing subject, executor,
claim basis, grant generation, provider policy or authority generation makes an
apply stale or conflicting.

An exact retry returns the immutable recorded outcome and attribution without
re-authorizing or reapplying it. `p2p mutation status --idempotency-key ...`
reports current postcondition drift separately from that historical outcome.

## Authority Rotation

Only the current root can rotate authority. Rotation advances generation once
and atomically writes the descriptor, append-only authority event and receipt:

```bash
p2p project authority rotate preview \
  --operation-key authority-rotation-001 \
  --display-name "Current project authority" \
  --format json

p2p project authority rotate apply \
  --operation-key authority-rotation-001 \
  --preview-token ... \
  --rotated-at 2026-08-25T15:00:00Z \
  --display-name "Current project authority" \
  --confirm --format json

p2p project authority rotate status \
  --operation-key authority-rotation-001 --format json
```

Changing mode or provider requires an explicit replacement authority ID. MCP
does not expose rotation apply; use a reviewed CLI or provider-controlled
administrative path.

## Hosted Trust Boundary

An external attestation is trustworthy only to the extent that the hosted
boundary is trustworthy. A server integration must:

1. authenticate the request;
2. authorize the exact project capability;
3. construct the context from server-side policy;
4. prevent clients from invoking the worker directly;
5. serialize writes and retain the returned receipt.

Filesystem or shell access remains outside this guarantee. P2P stores no
provider credentials or mutable hosted grant mirror and performs no provider
network request while validating a context.
