# Requirements - Support Typed Authority Context In Governed Mutations

## Scope

Introduce a transport-neutral authority contract for governed P2P mutations.
Standalone projects continue to resolve authority through local P2P policy;
hosted systems may instead attach a typed external authorization attestation.
P2P validates and records that attestation but does not become an identity,
membership or grant server.

## Origin

- Source: owner-approved grant and delegated-decision architecture review.
- Target train: P2P Engine `0.5.0`, workspace schema 4.
- Related WaveKit change: `establish-project-capability-grants`.
- Coordinates with: the domain, project-structure, classification, readiness,
  export, replacement, merge, restore and surface-convergence feature set.

## In Scope

- Versioned `AuthorityContext` and project authority descriptor contracts.
- Local-policy and external-attestation authority modes.
- Explicit project authority, authorized subject and executor identities.
- Stable governed-mutation capability identifiers.
- Binding authority evidence to preview, apply, idempotency, events and receipts.
- Full proposal-decision integration as the first delegated vertical slice.
- CLI JSON, MCP stdio, documentation, generated-agent and wheel-fixture coverage.

## Out Of Scope

- User authentication, OAuth, organizations, memberships or grant management.
- Replicating a hosted provider's current grant list into `.p2p`.
- Calling WaveKit or another provider to verify an attestation online.
- Treating an external attestation as cryptographic proof issued by P2P.
- Multiple accountable project owners or quorum decisions.
- Delegating structural, domain, classification, export or replacement
  capabilities in the initial WaveKit policy.

## Public Surface And MCP Impact

- CLI impact: breaking, permission-gated JSON input/output additions for
  governed mutations; local human commands preserve standalone owner flows.
- MCP impact: consent-gated tools carry the same typed authority semantics and
  never infer authority from transport identity alone.
- Storage impact: workspace schema 4 stores a project authority descriptor and
  audit-safe authority evidence on governed mutation events and receipts.
- Agent-facing behavior: generated guidance distinguishes authority, authorized
  subject, executor, capability and external attestation limitations.
- MCP parity decision: required for every governed mutation that already has an
  MCP write surface; absent surfaces remain explicit deferrals.

## Functional Requirements

### Project Authority Descriptor

- R001: Every schema-4 project SHALL have exactly one current project authority
  descriptor with a stable opaque authority ID, mode and positive generation.
- R002: Authority mode SHALL be the tagged union `local_policy` or
  `external_attestation`; unknown modes or fields SHALL fail closed.
- R003: A local-policy descriptor SHALL identify the local P2P policy version
  used to resolve actor authority.
- R004: An external-attestation descriptor SHALL identify the external provider
  and provider policy version without storing provider credentials.
- R005: Changing the authority root, provider or authority mode SHALL advance
  the authority generation through a separate governed operation; changing a
  display name SHALL NOT change the authority identity.
- R006: Runtime contracts SHALL use neutral technical authority identifiers and
  SHALL NOT encode a mutable owner identity in names such as `wk-owner-*`.

### Typed Authority Context

- R007: Every integrated governed mutation SHALL declare one stable required
  capability from the P2P governed-capability registry.
- R008: `AuthorityContext` SHALL contain its schema version, mode, project
  authority ID and generation, authorized subject, executor, required
  capability claims and one operation-specific authorization decision ID.
- R009: Authorized subject and executor SHALL be distinct typed concepts; the
  executor MAY be the subject, a user-controlled agent or an MCP client, but
  the technical worker process SHALL NOT replace the initiating identity.
- R010: Actor and executor identifiers SHALL be opaque, bounded, log-safe and
  project-scoped; raw database IDs, access tokens, cookies and secrets SHALL be
  rejected.
- R011: Every capability claim SHALL name the exact capability and authorization
  basis `root_authority`, `local_policy` or `capability_grant`.
- R012: A `capability_grant` basis SHALL include an opaque grant reference and
  positive grant generation; a root-authority basis SHALL bind the current
  authority generation and SHALL NOT fabricate a grant reference.
- R013: External-attestation context SHALL include provider ID, provider policy
  version and authorization timestamp and SHALL be described as a provider
  claim recorded by P2P, not as authorization independently proven by P2P.
- R014: P2P SHALL validate context schema, bounds, capability match, authority
  descriptor match and internally consistent subject/executor/basis fields
  without invoking the external provider.
- R015: Context mode SHALL match the current project authority descriptor;
  mismatched provider, authority ID or generation SHALL fail before mutation.

### Local And Hosted Semantics

- R016: In `local_policy` mode, P2P SHALL continue to resolve the authorized
  subject against local project actors, roles and consent policy.
- R017: A standalone local owner SHALL remain able to perform all operations
  currently reserved to the owner without configuring any hosted provider.
- R018: In `external_attestation` mode, P2P SHALL NOT require a synchronized
  copy of provider memberships or grants and SHALL NOT reinterpret provider
  grant state as local P2P roles.
- R019: Control of the local filesystem or CLI process SHALL remain outside the
  hosted authorization guarantee; server deployments MUST protect invocation
  of the worker and creation of external attestations.

### Preview, Idempotency And Audit Binding

- R020: Preview SHALL bind the complete normalized authority context, required
  capability set and authority descriptor generation into its semantic token.
- R021: Apply SHALL resubmit the exact authority context used by preview;
  changed subject, executor, basis, grant generation, policy version or
  capability SHALL invalidate apply.
- R022: The authority-context digest SHALL participate in request fingerprint,
  operation-key divergence detection, receipt identity and recovery status.
- R023: Exact replay SHALL return the original result and original authority
  evidence even when current external grant state later changes.
- R024: Governed events and receipts SHALL persist an audit-safe authority
  projection containing subject, executor, capability, basis, provider,
  authority generation and opaque evidence references, but no secret material.
- R025: Read/status contracts SHALL distinguish `authorization_denied`,
  `authority_context_invalid`, `authority_generation_stale`,
  `capability_mismatch` and `operation_key_conflict` without leaking private
  provider state.

### Proposal Decision Vertical Slice

- R026: Proposal accept, reject, defer, revoke, reinstate and other
  authority-creating decision applies SHALL require capability
  `proposal.decide`.
- R027: A proposal decision in external-attestation mode MAY name a delegated
  non-owner subject when a structurally valid `proposal.decide` grant claim is
  supplied; the event SHALL attribute the decision to that subject rather than
  to the project authority root.
- R028: The executor SHALL be recorded independently from the decision subject
  for browser, CLI-agent and MCP-agent initiated decisions.
- R029: A decision that overrides a failed or insufficient readiness gate SHALL
  require both `proposal.decide` and `proposal.readiness.override`; external
  policy v1 SHALL accept the override claim only with root-authority basis.
- R030: Local-policy proposal decisions SHALL preserve current owner authority,
  executor validation, preview/apply and consent behavior.

### Capability Registry And Forward Contract

- R031: The schema-4 governed-capability registry SHALL define at least
  `project.initialize`, `project.authority.rotate`, `project.domain.change`,
  `project.structure.edit`,
  `project.memory.classify`, `project.structure.retire`,
  `project.structure.replace`, `project.structure.merge`,
  `project.structure.restore`, `project.vertical.export`, `proposal.decide`
  and `proposal.readiness.override`.
- R032: Each registry entry SHALL declare operation family, local-policy rule,
  supported authority modes and whether an external root-authority basis is
  required by the P2P contract.
- R033: The registry SHALL NOT encode WaveKit membership roles or decide which
  WaveKit grants are delegable.
- R034: Every new schema-4 governed mutation SHALL declare its capability and
  authority-context behavior before gaining CLI or MCP apply support.
- R035: Read-only inspection SHALL NOT require a mutation AuthorityContext;
  transport/application authorization remains the caller's responsibility.
- R036: `project.initialize` SHALL use a bootstrap authority context containing
  the candidate descriptor; successful initialization SHALL persist that exact
  descriptor atomically with project state.
- R037: Local initialization SHALL create a local-policy descriptor, while
  external initialization SHALL require a provider-supplied opaque authority
  root and root-authority claim; the normal current-descriptor match begins
  after bootstrap.
- R038: Authority descriptor rotation SHALL be a receipt-backed governed
  mutation declaring `project.authority.rotate` and requiring current
  root-authority basis.
- R039: Rotation SHALL preserve the authority ID unless an explicit provider or
  mode replacement is requested, SHALL advance generation exactly once and
  SHALL bind previous/new descriptor, actor, executor and operation key.
- R040: Descriptor, rotation event and receipt SHALL commit atomically and SHALL
  support exact replay, status and interrupted-transaction recovery.

## Non-Functional Requirements

- N001: Authority normalization and digest generation SHALL be deterministic
  across supported Python versions and installed wheels.
- N002: Authority validation SHALL occur before any persistent mutation and
  SHALL add no network dependency.
- N003: Public authority payloads and errors SHALL be bounded and safe for
  structured logs after caller authorization.
- N004: Core mutation services SHALL remain independent from CLI, MCP and any
  WaveKit implementation package.
- N005: Receipt recovery SHALL never re-authorize or re-apply a mutation already
  proven applied; it SHALL only reconcile the immutable recorded outcome.
- N006: Workspace validation SHALL detect missing, malformed or contradictory
  authority descriptors and governed events.

## Edge Cases And Errors

- External context supplied to a local-policy project or the inverse.
- Stale root-authority or grant generation after preview.
- Delegated subject removed by the provider after a mutation was applied.
- Executor differs between preview and apply.
- A client attempts to claim a capability not required by the operation.
- Readiness override supplied by a delegated decision subject.
- Lost apply response followed by grant revocation and retry.
- Exact operation replay after provider policy-version change.
- Malformed, oversized or secret-bearing opaque references.
- Legacy `wk-owner-*` authority identifiers in a schema-4 workspace.

## Acceptance Criteria

- AC001: Local standalone owner decision workflows remain functional without a
  hosted provider or grant mirror.
- AC002: A valid external `proposal.decide` attestation can authorize a
  delegated decision and records subject and executor separately.
- AC003: The same delegated subject cannot perform a readiness override without
  a root-authority `proposal.readiness.override` claim.
- AC004: Changed authority evidence invalidates preview/apply and divergent
  operation-key reuse without changing project state.
- AC005: Lost-response replay returns the original receipt and attribution even
  after the external grant is revoked.
- AC006: P2P performs no provider network call and stores no provider secret or
  mutable grant list.
- AC007: Every coordinated domain/structure feature declares its governed
  capability and no feature hard-codes a WaveKit owner check in P2P services.
- AC008: CLI, MCP, generated-agent guidance, maintained docs and installed-wheel
  fixtures describe the same authority semantics.
- AC009: Local and externally attested initialization each create exactly one
  matching authority descriptor without requiring pre-existing project state.
- AC010: Authority rotation advances generation once, invalidates old-context
  apply and safely reconciles a lost response without splitting descriptor and
  receipt state.
