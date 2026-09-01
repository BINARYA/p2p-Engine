# Project Application And Storage Ports

P2P Engine separates project behavior from local persistence. CLI and MCP open
the same `ProjectApplicationService`; it validates the project storage
selection, opens exactly one adapter and exposes typed queries and governed
Units of Work. `P2PWorkspace` remains only as a compatibility facade.

```text
CLI / MCP / compatibility callers
                |
       ProjectApplicationService
                |
 repository | Unit of Work | snapshot | blob | backup | migration ports
                |
       selected filesystem adapter
```

The current product has one implemented adapter: `filesystem`. This feature
does not add another backend and never dual-writes. A later adapter must
implement the same semantic contracts before it can be compared or selected.

## Replica-Local Selection

Fresh initialization writes:

```yaml
project_storage:
  contract: p2p-project-storage/v1
  project_uuid: 00000000-0000-0000-0000-000000000001
  adapter: filesystem
  schema_version: 1
```

The real UUID is the stable canonical project UUID. The manifest lives at
`.p2p/local/storage.yml`; it is not a field in `.p2p/project.yml`. Open rejects
malformed contracts, unsupported schemas, unavailable adapters, UUID mismatch
and contradictory backend artifacts. Existing filesystem projects without the
manifest may open through a validated fallback that performs no write.
Explicit `p2p init ... --storage-adapter filesystem` adopts that selection.

Identity adoption or derivation updates the canonical identity, local replica
identity, project hint and storage manifest in the same atomic mutation. This
prevents a successful identity transition from making the selected store
unopenable.

## Semantic Contracts

- `ProjectStateRepository` provides a consistent canonical snapshot, stable
  revision, typed entity lookup and bounded typed query.
- `ProjectUnitOfWork` requires an expected revision and one project UUID. It
  stages a complete logical command result and activates every changed entity
  and blob under the existing durable filesystem transaction.
- stale revisions fail before activation; competing writers have a bounded
  wait; failed replacement rolls back or reports explicit recovery state.
- portable bundles contain canonical state and managed blobs, never the
  adapter manifest or live storage files.
- physical backups retain the replica-local adapter manifest and exclude live
  transaction locks.

Storage errors have stable categories such as unavailable adapter, identity
mismatch, stale revision, busy, integrity failure and recovery required.
Detailed diagnostics stay internal; public CLI/MCP responses do not expose
absolute paths, SQL or backend credentials.

## Supported Integration Boundary

The Python ports are internal contributor APIs. They are not the WaveKit
integration boundary and do not create a cross-repository dependency. Server
consumers use the immutable, versioned P2P CLI JSON contract, operation keys,
receipts and explicit recovery behavior.

Generated local agent instructions describe CLI/MCP operations only. They do
not select an adapter or instruct agents to inspect YAML, database, journal or
WAL internals.

Retained structure history and merge/restore transitions follow the same
boundary. Public callers address an exact release/bundle digest or retained
structure revision/checksum. The selected adapter atomically stores the new
forward structure revision, prior snapshot, event, affected memory and receipt;
no public plan or result contains a physical path, SQL statement or backend
name. The current product continues to select only the filesystem adapter.
