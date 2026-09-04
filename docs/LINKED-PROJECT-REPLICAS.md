# Linked WaveKit Project Replicas

P2P Engine can materialize a complete local replica while WaveKit remains the
only project authority. A linked replica preserves `project_uuid`, receives a
distinct `replica_id`, and tracks one verified WaveKit authority epoch,
revision and cursor. It is not an independent copy and cannot silently become
standalone while offline.

Before every linked catch-up or mutation, P2P verifies the selected adapter's
integrity and the canonical semantic/blob digests against the last confirmed
WaveKit evidence. Divergence is quarantined rather than merged. See
[Linked Replica Drift And Recovery](LINKED-REPLICA-DRIFT.md) for classification,
forensic backup, authoritative rebuild and the bounded owner-confirmed command
reconciliation workflow.

This lifecycle is separate from authority transfer:

- transfer moves authority for an existing standalone project to WaveKit;
- clone or attach creates another local replica of an already authoritative
  WaveKit project;
- register-copy gives a physically copied replica a new operational identity;
- move preserves a replica identity only after WaveKit confirms that the old
  physical copy is deactivated.

## Clone And Attach

Authenticate first with the owner-run OAuth Device Flow. Credentials remain in
the operating-system keyring and are never written below the project root.

```bash
p2p auth login https://wavekit.example --format json

p2p wavekit clone wk_PROJECT \
  --server https://wavekit.example \
  --account-profile wavekit:user:ACCOUNT_UUID \
  --operation-key owner:clone:001 \
  --target ./workspace --confirm --format json
```

`attach` uses an existing workspace without `.p2p` and preserves its user
files:

```bash
p2p wavekit attach wk_PROJECT \
  --server https://wavekit.example \
  --account-profile wavekit:user:ACCOUNT_UUID \
  --operation-key owner:attach:001 \
  --root ./existing-workspace --confirm --format json
```

Both operations negotiate `p2p-linked-replica/v1`, register a fresh replica,
freeze one exact remote revision, and download the canonical bundle plus every
referenced managed blob. P2P verifies size and SHA-256 limits, project and
replica identity, authority epoch, semantic digest, blob-manifest digest and
the byte content returned by the separate blob endpoints.

Materialization occurs in a resumable sibling staging directory. P2P invokes
the selected storage adapter there, validates the complete project, records the
non-secret binding, and only then atomically renames the staged `.p2p` into the
workspace. A failed or interrupted download leaves no active partial replica.
The staging directory is retained for retry or diagnostics.

The current product line selected the filesystem adapter. The CLI keeps the
explicit `--storage filesystem` choice so the public contract remains
backend-neutral; it rejects unavailable adapters rather than guessing from
files.

## Binding And Freshness

Inspect replica state without network access:

```bash
p2p wavekit status --root . --format json
```

The replica-local binding stores only:

- server instance and URL;
- remote project ID and stable `project_uuid`;
- local `replica_id`;
- authority epoch;
- last applied remote revision and cursor;
- verified semantic and blob-manifest digests;
- a non-secret account-profile reference;
- access/freshness state and last successful verification time.

It never stores access tokens, refresh tokens, passwords, local absolute paths,
backend database files, snapshot archives or remote project memory.

P2P exposes one shared replica service. Normal one-shot CLI and linked MCP
reads run the same catch-up automatically; users can also inspect or invoke it
explicitly for diagnostics and recovery:

```bash
p2p sync status --root . --format json
p2p sync catch-up --root . --format json
p2p sync recover --root . --format json
p2p watch --root .
p2p watch --max-events 10 --root . --format json
```

The legacy `p2p wavekit sync catch-up|recover` paths remain aliases. Catch-up
requests contiguous logical change batches after the committed local cursor.
P2P validates contract, project UUID, replica ID, authority epoch, revision
order, batch digest, semantic state digest and every referenced blob before it
atomically commits canonical effects, inbox marker and cursor. A duplicate is
harmless; a gap is rejected. If retention removed the required batch, P2P
downloads a complete replacement snapshot, validates it in staging and swaps
it atomically. The previous `.p2p` is retained below
`.p2p/local/replica-recovery/` as forensic evidence; it is neither canonical
memory nor part of portable bundles.

An offline read may use the last confirmed local state only with
`source=local-cache`, `stale=true`, the last revision and verification time.
Every offline mutation fails with `P2P_REMOTE_AUTHORITY_UNAVAILABLE`; no hidden
outbox or optimistic confirmed state is created. Expired login suspends the
link, and revoked access remains `access-revoked` rather than reverting the
project to standalone.

Online linked mutations never execute optimistically against local memory.
Registered MCP domain tools send a typed command containing stable operation
and idempotency identity, project/remote/replica identity, authority epoch,
observed project revision, entity preconditions and a versioned domain payload.
WaveKit derives actor and capability from authentication, serializes only the
short final commit, and returns an immutable receipt. P2P then catches up the
durable feed before returning confirmed freshness. Reusing an operation or
idempotency key for different work fails explicitly.

`p2p watch` consumes authenticated SSE notifications, but every notification is
only a wake-up for HTTP feed catch-up. Lost, duplicate or reordered SSE events
cannot lose data or advance the cursor. Heartbeats and ephemeral presence never
enter P2P memory, bundles, batches or local inbox state. A later WebSocket
transport can carry the same event references without a memory migration.

## Physical Move And Copy

Copying `.p2p` bytes cannot create a second valid writer. The owner must choose
one of these explicit outcomes:

```bash
p2p wavekit replica move \
  --operation-key owner:move:001 --confirm --root . --format json

p2p wavekit replica register-copy \
  --operation-key owner:copy:001 --confirm --root . --format json

p2p wavekit replica read-only --root . --format json
```

Move preserves the replica ID only after a server-confirmed deactivation of the
old copy. Register-copy downloads and activates a fresh snapshot with a new
`replica_id`. Read-only is a local forensic state and never grants authority.

## CLI And MCP Boundary

Clone, attach, move and copy registration remain explicitly confirmed owner CLI
operations. MCP `stdio` exposes replica diagnostics only through:

- `p2p_linked_replica_status`;
- `p2p_linked_replica_catch_up`.

There is no MCP clone, attach, replica move or copy-registration tool. Generated
`linked-local` instructions use CLI and MCP `stdio` through P2P application
services. Domain MCP writes remain semantic tools; no raw feed, cursor, blob,
batch, command-envelope, initialization or compaction tool is registered. Agent
instructions never expose `.p2p`, YAML paths, SQL rows, journals or WAL files.

WaveKit supplies authorization, the operation queue, notification outbox,
registration, immutable snapshots, blobs, cursor delivery and revocation. The
P2P project root remains canonical for project state, revision head, batches
and receipts. PostgreSQL may retain WaveKit operations and delivery metadata,
but not a second mutable copy of P2P project memory or batch payloads. The
protocol transfers logical contracts, never a server filesystem layout or
database schema.

On the server, the trusted worker initializes and reads the P2P-owned feed
through versioned JSON commands:

```bash
p2p project replication initialize --authority-epoch 2 \
  --project-revision 0 --retention-batches 2048 --confirm --format json
p2p project replication status --format json
p2p project replication operation-status OPERATION-ID --format json
p2p project replication feed --after-revision 10 \
  --replica-id REPLICA-ID --limit 64 --format json
p2p project replication compact --retain-after-revision 100 \
  --confirm --format json
```

WaveKit passes a validated command document through the hidden worker-only
`--replication-command-envelope` option and invokes only its reviewed CLI
allowlist. That option requires the `p2p-cli/v1` JSON boundary and grants no
authority by itself. The final filesystem lock rechecks identity, epoch and
project/entity preconditions, then commits canonical state, head, batch,
receipt and idempotency evidence together.

Snapshot fallback still uses `p2p project memory snapshot-export`. It produces
a bundle and managed blobs in isolated temporary storage and returns only
relative artifact references. WaveKit serves those artifacts but never opens
the project root or parses the bundle format itself. Change-feed compaction is
explicit and does not delete immutable operation receipts or WaveKit audit.
