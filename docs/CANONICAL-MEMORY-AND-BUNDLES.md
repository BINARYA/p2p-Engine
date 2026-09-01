# Canonical Project Memory And Bundles

P2P Engine exposes project memory as a logical, versioned contract independent
of the storage backend. The filesystem adapter reads the `.p2p/` document tree;
the opt-in experimental SQLite adapter reads semantic tables and canonical JSON.
Callers must not depend on paths, YAML layout, SQLite tables, journals, or WAL
files. CLI and MCP contracts remain the supported boundary.

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

A physical backup (`p2p-physical-backup/v1`) is an adapter-specific recovery
artifact for one local store. It retains portable and replica-local durable
state, but excludes active workspace-transaction locks and recursive backup
trees. It is not an interchange or synchronization protocol.

For SQLite, a physical backup contains a clean database produced through the
online backup API, the storage manifest and referenced external blobs. It never
copies a live main database alone and never includes WAL/SHM/journal files.
Its manifest, semantic digest and referenced blob set are derived from that
exact copied database revision, even if a writer commits during backup. Archive
verification checks both the physical archive hash and the declared semantic
digest. Portable-bundle metadata is likewise returned from the same snapshot
that was encoded, rather than from a second live read.
SQLite-authoritative mutation receipts are therefore retained by a physical
backup as database state. They remain replica-local operational history and are
still excluded from canonical memory and portable bundles.

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

For filesystem projects, `inspect` classifies every durable `.p2p` file.
Unknown paths, symlinks, unsupported documents, secret-shaped fields in
canonical or replica-local state, and oversized logical records block
snapshots, bundles and backups. Archives are never overwritten and must be
written outside `.p2p`.

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

p2p project memory recovery-apply \
  --recovery-id <exact-recovery-uuid> \
  --token <exact-recovery-token> --actor owner \
  --action rollback --confirm --format json
```

Apply verifies the exact archive and token, creates a verified pre-restore
physical backup, builds a separate staging store, validates its semantic digest,
identity, constraints and blobs, and swaps the validated store atomically. The
filesystem adapter also uses its workspace mutation lock and domain validation;
SQLite serializes the maintenance operation and uses its explicit fence. A
failure before or during activation rolls back to the previous active store.

If the process terminates before that handled rollback completes, ordinary
project open remains fenced. `recovery-status` can still read the versioned
marker without opening the selected adapter and reports the exact recovery ID,
confirmation token, operation, phase and verified source identity. Only a
current source-project owner may run `recovery-apply`; the first contract offers
only an explicit rollback to the verified source state. The same protocol
covers interrupted SQLite restore, identity replacement, initial filesystem to
SQLite activation and schema migration. It rejects a live forward writer,
changed recovery artifacts, unsafe paths and stale or mismatched tokens. A
durable completion receipt makes a lost recovery response and a crash during
cleanup safe to replay. A different verified current owner may finish cleanup
or recover a lost acknowledgement with the exact same ID and token; the durable
result preserves the original recovery actor.

Recovery does not guess whether to continue forward. In particular, an
interrupted schema migration is rolled back before a fresh migration attempt.
Legacy v1 markers remain visible for diagnosis but are not applied
automatically. Do not delete a marker, lock, staging directory or recovery
database by hand.

Bundle restore replaces portable logical state and removes stale derived views;
it preserves target-local replica state and generated integrations. Physical
restore recreates the exact backed-up local store. Never unzip either archive
into `.p2p` manually.

## MCP Boundary

MCP intentionally exposes only read-only operations:

- `p2p_canonical_memory_inspect`;
- `p2p_canonical_memory_verify`;
- `p2p_project_bundle_export_metadata` (computes metadata without writing an archive);
- `p2p_project_archive_verify`.

MCP cannot choose an output path, export, back up, restore, recover or activate
memory. A future MCP restore/recovery mutation requires a separate consent-safe
contract.

## Managed Blobs And External References

Managed blobs live in the adapter's content-addressed store and are referenced
as `{"kind": "managed_blob", "digest": "sha256:<digest>"}`. Every reference
must have exactly one matching blob manifest entry and payload; unreferenced or
missing blobs invalidate the bundle. Identical content is transferred once.

External paths and URIs remain references unless explicitly imported as a
managed blob. Source code, tests, docs, specs, Git metadata and arbitrary files
outside `.p2p` are never swept into a bundle.

## Adapter Contract

Storage adapters implement typed project-state queries, revision-checked Units
of Work, snapshots, blobs, physical backup/restore, migration metadata and
capability reporting. The codec, semantic digest, bundle contract and restore
policy do not expose physical locators. Every adapter must pass the same
semantic, atomicity, recovery and round-trip contract tests.
