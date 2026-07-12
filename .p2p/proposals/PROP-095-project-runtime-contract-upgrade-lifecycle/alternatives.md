# Alternatives Considered

## 1. Leave Runtime Contract Changes As Manual Edits

Manual edits to `.p2p/project/runtime.yml` followed by validation would keep the
implementation small, but they would not provide a controlled lifecycle for
coordinating the derived setup guide, stale-state protection, impact
classification, owner authorization, or collaborator-facing diagnostics.

This alternative is rejected because it recreates the core problem: an owner can
change the required runtime line without a structured preview of who is affected
and without a coordinated update of `P2P-SETUP.md`.

## 2. Provide One `p2p runtime contract update` Command

A single command could combine preview, confirmation, and mutation. It is simpler
to document, but it makes read-only agent workflows weaker and encourages a
mutation-first interaction model.

This alternative is rejected in favor of separate commands:

- `p2p runtime contract preview`
- `p2p runtime contract apply`

The split lets agents and non-owner collaborators prepare a complete technical
request without acquiring owner authority or mutating project state. `apply`
remains the only authoritative mutation path.

## 3. Automatically Install Or Upgrade P2P Engine

An automatic updater could try to resolve collaborator drift directly. This would
mix project governance with environment management and would need to own package
sources, network consent, installation paths, rollback, and platform-specific
failure behavior.

This alternative is rejected. PROP-095 updates the project runtime contract and
diagnoses the local mismatch. It does not install, upgrade, downgrade, or
reconcile the active P2P Engine runtime.

## 4. Require A Linked P2P Proposal Or Decision For Every Update

Mandatory proposal linkage would create a strong governance trail, but it is too
heavy for routine maintenance and may be circular when the active runtime is
already outside the current range and cannot safely perform ordinary governed
writes.

This alternative is rejected for the first implementation. Runtime contract
updates are owner-controlled governed operations with preview, confirmation,
reason where required, stale-preview protection, and authority checks. Linking an
existing decision remains optional for traceability. A future project policy may
make decisions mandatory for selected impacts such as runtime-line changes.

## 5. Persist A Single-Use Preview Token

A persisted token would allow strict consumption semantics, but it would require
additional state writes during preview and would make read-only agent workflows
harder.

This alternative is rejected. The selected design uses a deterministic stateless
expected-state token. The token binds protected project state and the proposed
contract update. It is not actor authority, consent, or a persisted approval.

## 6. Allow Replacement Of An Unmanaged `P2P-SETUP.md`

An override flag could let owners replace an existing human-written setup guide
while changing the runtime contract. That would introduce a distinct adoption or
replacement capability with backup, merge, attribution, and data-loss concerns.

This alternative is rejected. If `P2P-SETUP.md` exists without the P2P-managed
marker, `apply` is blocked before mutation. Adoption or replacement of an
unmanaged setup guide is a separate future capability.

## 7. Block Updates When Release Availability Cannot Be Verified

Release availability checks can prevent typos, but they depend on local metadata
freshness and optional external state. Making them mandatory would turn a
contract update into a release-discovery workflow.

This alternative is rejected. PROP-095 may report `release_availability:
unverified`, but that finding is informational when the proposed contract is
otherwise valid.

## Selected Approach

PROP-095 defines a contract-update lifecycle, not an installation lifecycle:

- read-only preview for owners, agents, and collaborators;
- owner-authorized apply with explicit confirmation;
- deterministic stateless stale-state protection;
- structured impact classification;
- coordinated updates to `runtime.yml` and managed `P2P-SETUP.md`;
- no mutation after activating a contract that excludes the active runtime;
- no implicit handling of unmanaged setup guides or untrusted current contracts.

## Tradeoffs

The selected approach adds command and test surface, but it keeps project state
changes explicit and reviewable. It does not solve environment installation by
itself; instead, it makes the project contract authoritative and tells the user
when their local runtime is no longer compatible.

The most important tradeoff is deliberate separation of responsibilities:
project owners may update the contract, while collaborators remain responsible
for installing a compatible P2P Engine version according to the generated setup
guide.
