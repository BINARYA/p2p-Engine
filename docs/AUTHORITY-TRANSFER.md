# Transfer Project Authority To WaveKit

P2P Engine can hand one standalone project to WaveKit without creating a new
logical project. The transfer preserves `project_uuid`; WaveKit becomes the
only authority and the original local memory becomes a `linked-local` replica.

This workflow is distinct from publishing a derived copy or asking WaveKit to
create an unrelated project. Those operations use different commands,
fingerprints and receipts.

## Preconditions

Transfer requires:

- a valid standalone identity with no remote binding;
- clean canonical-memory/recovery state and every managed blob present;
- the selected storage adapter and a deterministic canonical bundle;
- a compatible WaveKit capability document;
- an authenticated account mapped to the requested owner profile;
- an operation key, exact preview token and owner confirmation.

Authenticate through the server-advertised OAuth Device Flow. P2P never asks
for a WaveKit password:

```bash
p2p auth login https://wavekit.example --format json
p2p auth status https://wavekit.example --format json
```

Access and refresh tokens live in the operating-system keyring. They never
enter `.p2p`, a bundle, generated instructions, CLI JSON or MCP output. Logout
deletes the credential without detaching the project; an affected linked
replica changes to `link-suspended` until device login succeeds again.

## Owner CLI Workflow

Preview is read-only. It validates local state, negotiates
`p2p-authority-transfer/v1`, checks authenticated eligibility and calculates a
deterministic transfer ID/fingerprint:

```bash
p2p project transfer preview \
  --server https://wavekit.example \
  --owner-profile profile:owner-1 \
  --operation-key owner:transfer-001 \
  --format json
```

The preview reports logical counts, digests, adapter, destination and authority
change. It contains no local paths, tokens or backend internals. Apply repeats
the exact inputs and preview token:

```bash
p2p project transfer apply \
  --server https://wavekit.example \
  --owner-profile profile:owner-1 \
  --operation-key owner:transfer-001 \
  --preview-token TOKEN \
  --confirm --format json
```

Do not start a second transfer after a timeout. Inspect or recover the same
session:

```bash
p2p project transfer status --format json
p2p project transfer status --server https://wavekit.example --format json
p2p project transfer recover --format json
```

`status` without `--server` reads only non-secret local state. Supplying the
server queries the authenticated remote session.

## Authority Boundary And Recovery

```text
standalone -> preflighted -> locally_fenced -> remote_staging
           -> remote_committed -> local_binding_pending -> linked
```

Local memory remains authoritative until WaveKit durably commits and returns
an activation receipt. During upload, a recoverable local fence blocks governed
writes against the previewed revision. Once the server session is `committed`,
WaveKit is authoritative even if the response or local cutover is lost.

Recovery queries the original `transfer_id`:

- `committed`: verify the receipt and finish local binding;
- `rejected`, `cancelled` or `expired`: release the fence and retain standalone
  authority;
- non-terminal: keep the fence and retry the same session later.

There is no automatic fallback from remote authority and no dual-write period.

## Payload And Receipt

The upload contains the deterministic canonical `.p2pbundle` and every
referenced managed blob requested by digest. It never sweeps source files or
uploads storage manifests, credentials, generated agent files, physical
backups, transaction journals, databases or WAL files.

The strict `p2p-authority-transfer-receipt/v1` receipt binds the transfer ID,
request fingerprint, project UUID, destination, remote project and replica IDs,
incremented authority epoch, remote revision/cursor, bundle/blob digests, exact
required blob set and non-secret account-profile reference. Only a receipt
matching every previewed value can atomically update the local identity,
binding, receipt and transfer state through the selected adapter.

## Linked-Local And MCP Boundary

After cutover, P2P refreshes only proven P2P-owned integration artifacts to
`linked-local`; user-owned content is preserved and reported. Agents are told
that WaveKit is authoritative, local reads may be stale and governed local
mutations are blocked. Replica catch-up and online WaveKit mutation routing are
separate later features.

MCP exposes only:

- `p2p_project_authority_transfer_eligibility`;
- `p2p_project_authority_transfer_preview`;
- `p2p_project_authority_transfer_status`.

There is deliberately no MCP transfer apply, upload, recover, login or logout
tool. Moving canonical authority remains an explicitly confirmed owner CLI
action.
