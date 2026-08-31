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
       resolver: exactly one authoritative adapter
                |
          filesystem | SQLite (experimental)
```

The experiment implements `filesystem` and an opt-in `sqlite` candidate.
Filesystem remains the default and SQLite is not a product selection until the
separate evaluation gate records `sqlite-go`. Comparison uses distinct project
instances: one project never writes both stores.

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
An owner may initialize a separate experimental project with:

```bash
p2p init "SQLite candidate" --starter generic --storage-adapter sqlite
```

Backend selection is deliberately a local owner CLI concern during the
experiment. MCP exposes no SQLite-specific tool and its initialization schema
does not let an agent choose the candidate backend.

That command first validates a complete logical state, creates
`.p2p/local/project.sqlite3` in staging, verifies it and atomically removes the
temporary canonical YAML/Markdown projection. Reopen uses the manifest and DB
metadata automatically. A DB/manifest UUID or schema mismatch, a simultaneous
canonical filesystem store, a maintenance fence, corruption, or an unsupported
multi-host network filesystem blocks the open. Existing filesystem projects do
not migrate automatically; the test-only import used by the experiment is not
the later governed migration workflow.

Legacy filesystem identity adoption remains one filesystem transaction. A
governed SQLite derivation changes the identity by fencing the previewed
revision, creating and verifying a new one-project database, backing up the old
database, and activating the new database together with its updated manifest.
Handled failures roll back; an incomplete rollback retains its maintenance
marker for explicit recovery.

## Semantic Contracts

- `ProjectStateRepository` provides a consistent canonical snapshot, stable
  revision, typed entity lookup and bounded typed query.
- `ProjectUnitOfWork` requires an expected revision and one project UUID. It
  stages a complete logical command result and activates every changed entity
  and blob under the selected adapter's durable transaction.
- stale revisions fail before activation; competing writers have a bounded
  wait; failed replacement rolls back or reports explicit recovery state.
- portable bundles contain canonical state and managed blobs, never the
  adapter manifest or live storage files.
- physical backups retain the replica-local adapter manifest and exclude live
  transaction locks.

The SQLite candidate uses a semantic hybrid schema, not a `path/content`
virtual filesystem. Identity, project/entity revisions, authority, relations,
structure assignments, receipts, operations and blob references have typed
columns, constraints and indexes; flexible entity documents use canonical
JSON. Blob bytes remain content-addressed under `.p2p/blobs/`.

SQLite enables foreign keys, WAL, full synchronous durability and a bounded
busy timeout. Readers may overlap on one host and writers serialize per
project. WAL/SHM/journal files are private runtime state and never enter a
bundle, sync payload or backup archive. Live backups use SQLite's online backup
API; restore uses a verified staging database, pre-restore backup, maintenance
marker and atomic activation. Schema version and applied DDL digest are recorded
in both SQLite metadata and the migration ledger. There is no released older
SQLite schema in this first candidate, but the backup-protected pre-versioned
v0-to-v1 rehearsal covers ordering and interrupted resume. Newer or fenced
schemas fail closed.

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

Mandatory application encryption is deliberately deferred. Local directory and
database permissions are restricted where the platform supports it, OS disk
encryption may be used, and credentials/tokens remain outside project state.
SQLite is a local single-host candidate only; it is not WaveKit server storage.
