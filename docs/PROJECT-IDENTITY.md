# Stable Project Identity

Every initialized P2P project has a globally unique, immutable `project_uuid`.
It identifies the logical project and is independent of its display name, slug,
directory, Git state, storage backend, machine, and any WaveKit identifier.

Inspect the current contract without writing:

```bash
p2p project identity status --format json
p2p project identity show --format json
p2p project identity transitions --format json
```

## Addressing Layers

| Value | Owner and scope | Meaning |
| --- | --- | --- |
| `ProjectUuid` | P2P project | Stable logical project identity. |
| project `id` and human keys | P2P project | Readable, project-scoped keys such as a slug or `PROP-104`; not global identity. |
| technical entity ID | P2P project | Identity of one proposal, choice, section, criterion, or other entity inside the project namespace. |
| `ReplicaId` | local materialization | Identity of one operational local copy; distinct copies of the same linked project require distinct replica IDs. |
| `ServerInstanceId` | remote provider | Stable address of one server installation; it is not a project ID. |
| `RemoteProjectId` | one server instance | Server-assigned address mapped to `project_uuid`; it is not a replacement for it. |
| authority subject/executor | authority provider | Who is authorized and which person, client, or agent executes a request. Neither is project identity. |
| lineage source UUID | historical project state | Provenance only; it grants no authority, membership, or synchronization rights. |

Revision values are also separate types. A source-memory SHA-256,
WaveKit/project revision, entity version, and authority epoch cannot be compared
across namespaces.

## Persisted Contract

The current filesystem adapter persists canonical project identity separately
from local replica state:

```text
.p2p/project.yml             project UUID hint and readable metadata
.p2p/project/identity.yml    canonical project UUID, display name, lineage
.p2p/local/replica.yml       local mode, replica ID, optional remote binding
```

These paths are adapter implementation details, not an editing interface. The
domain DTO and CLI/MCP outputs contain no filesystem path, YAML, SQLite,
PostgreSQL, Git, or credential fields. A future storage adapter must pass the
same adapter-contract tests without changing public semantics.

The current retained backend is filesystem storage. SQLite is a later candidate
and is not enabled by this feature.

## Lifecycle Rules

- New initialization creates a new project UUID and local replica ID.
- Rename, path move, same-project backup, and same-project restore preserve the
  project UUID.
- Transfer to a server preserves the project UUID and may add a separate remote
  project address. The implemented WaveKit handoff increments the authority
  epoch and records the originating linked replica from a verified receipt.
- A copied linked materialization requires a new replica ID if the old copy may
  remain operational. A true move may preserve it after the old copy is retired.
- Copying bytes does not choose identity intent. A duplicate operational UUID
  and replica pair remains ambiguous until the owner selects same-instance,
  read-only, new-replica where supported, or independent derivation.
- Derive and detach create a new project UUID, a new replica ID, remove active
  remote binding, and may retain typed historical lineage.
- Suspend preserves project and replica identity plus the binding address.

Inspect a known duplicate pair with:

```bash
p2p project identity copy-check \
  --observed-project-uuid UUID \
  --observed-replica-id UUID \
  --intent read-only \
  --format json
```

The command classifies the pair; it does not register a replica or infer that
another copy has been retired.

## Explicit Derivation

An independent copy uses a root-authorized, receipt-backed two-phase mutation:

```bash
p2p project identity derive preview \
  --operation-key local:derive-001 \
  --actor owner --format json

p2p project identity derive apply \
  --operation-key local:derive-001 \
  --preview-token TOKEN \
  --actor owner --confirm --format json
```

Use `--no-retain-lineage` to omit historical provenance, or
`--lineage-visibility private` to retain private lineage. Exact replay returns
`already_applied`; changed inputs with the same operation key fail as an
idempotency conflict. A stale preview does not write.

## Explicit Adoption Of Identity-Less Development State

An initialized development fixture created before this contract reports
`adoption_required` and ordinary governed mutations fail closed. Adoption is
never implicit:

```bash
p2p project identity adopt preview \
  --operation-key local:adopt-001 \
  --actor owner --format json

p2p project identity adopt apply \
  --operation-key local:adopt-001 \
  --preview-token TOKEN \
  --actor owner --confirm --format json
```

Apply writes the exact preview atomically, records a mutation receipt, and
retains the pre-adoption project manifest in a protected internal backup. An
incomplete, malformed, duplicated, self-referential, or contradictory identity
is invalid rather than silently adopted or repaired.

This adoption path exists for fixtures and development projects. It is not a
general workspace-schema migration mechanism.

## MCP Parity

Read-only tools mirror the CLI DTOs:

- `p2p_project_identity_show`
- `p2p_project_identity_status`
- `p2p_project_identity_transitions`
- `p2p_project_identity_copy_check`

Adopt and derive expose preview plus consent-gated apply tools. Consent is bound
to `project-identity@preview-token`; apply still requires the exact operation
key, token, actor, root authority, and explicit confirmation. There is no raw
identity setter in CLI, MCP, or the application service.

## Security And Recovery

Identity records, public outputs, receipts, and generated agent guidance do not
contain credentials, access tokens, cookies, or private keys. Remote bindings
contain only bounded opaque addresses.

Identity-changing writes use the common atomic workspace journal. A handled
failure rolls back every target. If external edits prevent rollback, the normal
workspace transaction recovery flow blocks unrelated mutations until explicit
owner recovery. Do not edit identity, replica, lineage, receipts, backups, or
transaction files manually.

The WaveKit transfer state, receipt and non-secret binding are replica-local.
Secrets remain in the operating-system keyring. See
[`AUTHORITY-TRANSFER.md`](AUTHORITY-TRANSFER.md) for the owner CLI, exact
receipt validation and lost-response recovery rule.

## Deliberate Limits

The current runtime implements the client/local halves of WaveKit authority
transfer and complete linked-replica clone, attach, catch-up, rebuild, move and
copy registration. It does not implement detach, offline mutation, realtime
collaboration, WaveKit's internal persistence, SQLite in the selected product
line, or automatic merging of divergent copies. See
[`LINKED-PROJECT-REPLICAS.md`](LINKED-PROJECT-REPLICAS.md).
