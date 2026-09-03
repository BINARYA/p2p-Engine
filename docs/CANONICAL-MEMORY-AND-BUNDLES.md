# Canonical Project Memory And Bundles

P2P Engine exposes project memory as a logical, versioned contract independent
of the storage backend. The current adapter reads the `.p2p/` filesystem tree,
but callers must not depend on paths, YAML layout, a future SQLite schema,
journals, or WAL files. CLI and MCP contracts remain the supported boundary.

## Three Different Artifacts

Canonical memory (`p2p-canonical-memory/v1`) is the logical project aggregate:
typed entities, explicit relations, retained lineage and content-addressed
managed blobs. Its semantic SHA-256 is stable across record order, YAML key
order, CRLF/LF line endings and canonically equivalent Unicode.

A project bundle (`p2p-project-bundle/v1`) is a deterministic portable archive.
It contains the complete logical aggregate and every referenced managed blob.
It does not contain `replica_id`, replica cursors, consent or mutation receipts,
credentials, personal settings, agent integrations, generated projections,
runtime locks, a live database, a journal or WAL/SHM files.

A physical backup (`p2p-physical-backup/v1`) is an exact recovery artifact for
one local store. It retains portable and replica-local durable state, but
excludes active workspace-transaction locks and recursive backup trees. It is
not an interchange or synchronization protocol.

The replica-local `.p2p/local/storage.yml` adapter manifest is therefore
included in a physical backup. It is excluded from canonical entities,
semantic digests and portable bundles. Changing only this manifest cannot
change the logical project checksum.

## Inspect, Verify And Export

```bash
p2p project memory inspect --format json
p2p project memory verify --format json
p2p project memory bundle-export --output project.p2pbundle --format json
p2p project memory archive-verify project.p2pbundle --format json
p2p project memory backup --output project.p2pbackup --format json
```

`inspect` classifies every durable `.p2p` file. Unknown paths, symlinks,
unsupported documents, secret-shaped fields in canonical or replica-local
state, and oversized logical records block snapshots, bundles and backups.
Archives are never overwritten and must be written outside `.p2p`.

Bundle archives use canonical JSON/JSONL, stable entry ordering, fixed ZIP
metadata, per-entry checksums, exact manifest counts and content-addressed blob
paths. Verification rejects missing, extra or duplicate entries, path
traversal, symlinks, unsupported contracts, invalid identity, broken relations,
lineage cycles, checksum failures, unmanifested blobs and decompression limits.

## Restore And Recovery

Restore preserves `project_uuid`; cloning or deriving a different project uses
the separate identity lifecycle. Restore is CLI-only and owner-controlled:

```bash
p2p project memory restore-preview project.p2pbundle \
  --operation-key restore-2026-08-31 --actor owner --format json

p2p project memory restore-apply project.p2pbundle \
  --operation-key restore-2026-08-31 --actor owner \
  --token <exact-preview-token> --confirm --format json

p2p project memory recovery-status --format json
```

Apply verifies the exact archive and token, acquires the workspace mutation
lock, creates a verified pre-restore physical backup, builds a separate staging
store, runs full project validation, writes an idempotency receipt and swaps the
validated store atomically. A failure before or during activation rolls back to
the previous active store. If rollback itself cannot complete, the recovery
marker and both physical trees are retained for explicit owner recovery.

Bundle restore replaces portable logical state and removes stale derived views;
it preserves target-local replica state and generated integrations. Physical
restore recreates the exact backed-up local store. Never unzip either archive
into `.p2p` manually.

## New-Root Materialization

A trusted server worker can create a separate physical replica of the same
logical project in a new empty staging root:

```bash
p2p project memory bundle-materialize project.p2pbundle \
  --root SERVER_STAGING_ROOT \
  --operation-key wavekit:transfer:TRANSFER_ID \
  --expected-project-uuid PROJECT_UUID \
  --expected-bundle-digest SHA256 --actor wavekit-worker \
  --confirm --format json
```

Unlike restore, materialization has no existing target state to preserve. It
keeps the bundle's `project_uuid`, creates a distinct deterministic
replica-local identity and filesystem storage manifest, validates the staged
project and records an idempotency receipt. It fails closed if the target is
not empty or the archive digest or identity differs. This is an installed-wheel
boundary for server orchestration; it is not exposed through MCP.

## Linked-Replica Server Snapshot

A trusted server worker can freeze an HTTP-servable replica snapshot without
exposing the project's physical storage to WaveKit:

```bash
p2p project memory snapshot-export \
  --root SERVER_PROJECT_ROOT \
  --output-directory NEW_SNAPSHOT_DIRECTORY \
  --format json
```

The new directory contains the canonical bundle and an exact copy of every
managed blob referenced by that bundle. The JSON contract
`p2p-linked-replica-server-snapshot/v1` returns semantic and blob-manifest
digests plus relative artifact references; it never reports the server root or
absolute paths. The command is read-only with respect to project memory,
backend-neutral, refuses existing or project-local targets and removes partial
staging after failure.

## MCP Boundary

MCP intentionally exposes only read-only operations:

- `p2p_canonical_memory_inspect`;
- `p2p_canonical_memory_verify`;
- `p2p_project_bundle_export_metadata` (computes metadata without writing an archive);
- `p2p_project_archive_verify`.

MCP cannot choose an output path, export, back up, restore or activate memory.
A future MCP restore requires a separate consent-safe contract.

## Managed Blobs And External References

Managed blobs live in the adapter's content-addressed store and are referenced
as `{"kind": "managed_blob", "digest": "sha256:<digest>"}`. Every reference
must have exactly one matching blob manifest entry and payload; unreferenced or
missing blobs invalidate the bundle. Identical content is transferred once.

External paths and URIs remain references unless explicitly imported as a
managed blob. Source code, tests, docs, specs, Git metadata and arbitrary files
outside `.p2p` are never swept into a bundle.

Authority transfer uses this same deterministic bundle plus eager digest-based
managed-blob upload. It never transfers a physical backup or replica-local
state. See [`AUTHORITY-TRANSFER.md`](AUTHORITY-TRANSFER.md).

## Adapter Contract

Storage adapters implement typed project-state queries, revision-checked Units
of Work, snapshots, blobs, physical backup/restore, migration metadata and
capability reporting. The codec, semantic digest, bundle contract and restore
policy do not expose physical locators. Every adapter must pass the same
semantic, atomicity, recovery and round-trip contract tests.
