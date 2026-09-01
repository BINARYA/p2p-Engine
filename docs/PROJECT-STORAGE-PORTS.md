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
canonical filesystem store, a maintenance fence, corruption, or a detected
unsupported multi-host network filesystem blocks the open. Existing filesystem
projects do
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
structure assignments, receipt identity/operation metadata, operations and blob
references have typed columns, constraints and indexes; flexible entity and
receipt payloads use validated canonical JSON. Blob bytes remain
content-addressed under `.p2p/blobs/`.

Public mutation receipts are authoritative SQLite records for SQLite projects.
The compatibility facade projects them into its private temporary filesystem so
the unchanged domain services can perform replay, conflict and postcondition
checks, but it does not persist receipt YAML beside the database. A new receipt,
its canonical state and its operation record commit in the same SQLite
transaction. Consequently a failed pre-commit leaves neither state nor receipt,
while a lost acknowledgement after commit reopens as an exact replay. Receipt
postcondition hashes are bound to the canonical filesystem projection produced
from the committed semantic state, rather than to incidental YAML key order.
Replica-local postconditions governed by those receipts, such as export markers
and protected identity-adoption backups, are stored with the receipt and
rematerialized if their filesystem copy is missing.

SQLite enables foreign keys, WAL, full synchronous durability and a bounded
busy timeout. Readers may overlap on one host and writers serialize per
project. Compatibility-facade calls also take the project transaction lock so
filesystem-only agent refreshes cannot race an identity transition; waiting is
bounded, failures are typed, and an interrupted lock uses the existing explicit
workspace-transaction recovery path. WAL/SHM/journal files are private runtime
state and never enter a bundle, sync payload or backup archive. Live backups
use SQLite's online backup API; restore uses a verified staging database,
pre-restore backup, maintenance marker and atomic activation. Schema version and
applied DDL digest are recorded in both SQLite metadata and the migration
ledger. There is no released older SQLite schema in this first candidate, but
the backup-protected pre-versioned v0-to-v1 rehearsal covers ordering and
interrupted rollback. Newer or fenced schemas fail closed.

Every destructive SQLite maintenance marker uses the same v2 recovery
contract. It binds source and target semantic identities, an operation-specific
phase, the active workspace transaction ID, collision-free staging/recovery
paths and a separate confirmation token. Restore, identity replacement,
initial activation and schema migration all leave enough durable source
evidence for owner-authorized rollback after a real process exit. Recovery
refuses to race a live writer and verifies database, manifest, blobs and
auxiliary/agent surfaces before removing operation-owned artifacts. Completion
is recorded before cleanup, so retry after a lost response or cleanup crash is
idempotent. Schema migration never performs an implicit post-crash resume: it
rolls back to the exact pre-migration database, after which a new migration may
be requested.

Authoritative database, manifest, blob, marker and auxiliary paths are checked
component by component. POSIX symlinks, Windows junctions/reparse points,
non-directory parents and paths resolving outside the project root fail closed.
Managed blob reads additionally avoid following the leaf and verify that the
file identity stays stable while bytes are read; publication is atomic,
no-clobber and durably synchronized where the platform supports directory
sync.

Storage errors have stable categories such as unavailable adapter, identity
mismatch, stale revision, busy, integrity failure and recovery required.
Detailed diagnostics stay internal and public responses do not expose SQL or
backend credentials. The local-only backup, restore and recovery CLI contracts
intentionally report paths to their physical artifacts, which may be absolute;
those mutating operations are not exposed through MCP.

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
Linux mount metadata and Windows UNC/remote-drive classification reject known
multi-host locations. A reported `unknown` filesystem type, including the
current best-effort result on macOS, is not proof that a volume is local; the
owner must keep the candidate database on a local single-host volume.
