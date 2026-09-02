# Linked WaveKit Project Replicas

P2P Engine can materialize a complete local replica while WaveKit remains the
only project authority. A linked replica preserves `project_uuid`, receives a
distinct `replica_id`, and tracks one verified WaveKit authority epoch,
revision and cursor. It is not an independent copy and cannot silently become
standalone while offline.

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

The P2P client checkpoint exposes one shared replica service. Until the paired
WaveKit domain-command interception is installed, catch up explicitly before
using cached project state:

```bash
p2p wavekit sync catch-up --root . --format json
p2p wavekit sync recover --root . --format json
```

Catch-up requests changes after the local cursor. The first protocol may return
a complete replacement snapshot for a normal advance, retention gap or local
corruption. P2P rebuilds it in staging and swaps it atomically. The previous
`.p2p` is retained below `.p2p/local/replica-recovery/` as forensic evidence;
it is not canonical memory and is not included in portable bundles.

An offline read may use the last confirmed local state only with
`source=local-cache`, `stale=true`, the last revision and verification time.
Every offline mutation fails with `P2P_REMOTE_AUTHORITY_UNAVAILABLE`; no hidden
outbox or optimistic confirmed state is created. Expired login suspends the
link, and revoked access remains `access-revoked` rather than reverting the
project to standalone.

The current capability matrix deliberately reports
`online-authoritative-write` as unavailable. P2P does not turn that missing
server integration into a local write: authoritative linked commands and
automatic per-domain-operation freshness are completed only with their paired
WaveKit contract and the durable-replication step.

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
operations. MCP `stdio` exposes only:

- `p2p_linked_replica_status`;
- `p2p_linked_replica_catch_up`.

There is no MCP clone, attach, replica move or copy-registration tool. Generated
`linked-local` instructions use CLI and MCP `stdio` through P2P application
services and never instruct an agent to inspect `.p2p`, YAML paths, SQL rows,
journals or WAL files.

WaveKit supplies authorization, registration, immutable snapshots, blobs,
cursor retention and revocation. It remains storage-implementation independent:
the protocol transfers logical P2P contracts, not a server filesystem layout
or database schema.
