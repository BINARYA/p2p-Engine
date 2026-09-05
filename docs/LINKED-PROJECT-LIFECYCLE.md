# Linked Project Lifecycle

P2P Engine implements the local/client half of the governed lifecycle for a
WaveKit-authoritative project. The commands in this document require a WaveKit
server that advertises the matching `p2p-project-lifecycle/v1` capability. A
server without that paired implementation fails closed; P2P never infers local
authority from unavailable remote services.

## Authority Invariants

- Suspend, archive, retention, deletion, revocation and network failure do not
  change the linked project's UUID or make its local cache authoritative.
- Detach creates an independent project with a new UUID, local authority and no
  source binding. The WaveKit source project remains unchanged.
- Create-from-local can transfer a standalone or detached project to WaveKit as
  a new remote while preserving that project's own UUID.
- Project publication creates immutable, versioned snapshot metadata. It does
  not create a live replica, grant authority or change synchronization.
- Local replica removal and remote project deletion are distinct operations.

Each mutating flow uses an owner-selected stable operation ID, a revision-bound
preview token, explicit confirmation and a verified server receipt. If a
response is lost, recover the same operation ID; do not retry under a new ID.

## Inspect And Preview

Inspect local evidence and authenticated remote state without writing:

```bash
p2p wavekit lifecycle status --root . --format json
p2p wavekit lifecycle status --root . --offline --format json
```

Prepare a lifecycle operation:

```bash
p2p wavekit lifecycle preview suspend \
  --operation-id owner:suspend:001 --root . --format json
```

The returned token is bound to the action, operation ID, project UUID, remote
project, authority epoch, exact revision and relevant target/lineage inputs.
A changed state or changed input invalidates it.

## Suspend And Resume

Suspension preserves the project UUID, remote project ID, replica ID, authority
epoch, cursor and binding, but disables linked writes. Resume authenticates,
renegotiates the server contract and catches up before returning the replica to
active use.

```bash
p2p wavekit suspend \
  --operation-id owner:suspend:001 --preview-token TOKEN \
  --confirm --root . --format json

p2p wavekit lifecycle preview resume \
  --operation-id owner:resume:001 --root . --format json
p2p wavekit resume \
  --operation-id owner:resume:001 --preview-token TOKEN \
  --confirm --root . --format json
```

Logout-related suspension follows the same identity rule. Neither form is a
detach or an authority transfer.

## Detach As An Independent Project

New-directory detach is preferred. P2P requests one exact remote snapshot,
downloads its canonical bundle and every managed blob, verifies all digests,
materializes the independent project in staging, assigns an explicit local
owner, verifies the result and only then publishes it.

```bash
p2p wavekit lifecycle preview detach \
  --operation-id owner:detach:001 \
  --target ../independent-project \
  --lineage-mode preserve-origin \
  --root . --format json

p2p wavekit detach \
  --operation-id owner:detach:001 \
  --preview-token TOKEN \
  --target ../independent-project \
  --local-owner mrjungle \
  --preserve-origin --as-independent --confirm \
  --root . --format json
```

Choose exactly one lineage flag:

- `--preserve-origin`: retain visible historical provenance;
- `--private-origin`: retain provenance marked private;
- `--drop-origin`: omit provenance irreversibly.

Retained canonical lineage records the source UUID, semantic source revision
and `detached-from` relation. The verified detach receipt separately binds the
source remote ID, server revision, authority epoch, timestamp and complete
snapshot/blob digests. Neither lineage nor the receipt grants source access,
membership or synchronization.

For same-directory detach, pass the current root as `--target`. P2P builds the
new project separately, preserves the old `.p2p` as a sibling backup and then
atomically switches the active `.p2p`. A failed preparation or verification
removes staging and leaves the linked source active. Do not delete the backup
until the owner has inspected the independent project.

The first lifecycle version does not expose emergency detach from an
unreachable or revoked server. Status reports the condition and keeps the
replica non-authoritative. A future emergency path would require an explicit
server/owner policy, a new UUID and unverified lineage; local cached bytes are
never an authorization bypass.

## Create A New WaveKit Project From Local

A detached project is locally authoritative and may use the existing authority
transfer protocol to become a new WaveKit project. The new remote gets its own
remote project ID, while the detached project's UUID and selected lineage stay
unchanged.

```bash
p2p wavekit create-from-local \
  --server https://wavekit.example \
  --owner-profile-ref wavekit:user:ACCOUNT_UUID \
  --operation-key owner:create-new:001 \
  --lineage-visibility preserved \
  --root ../independent-project --format json

p2p wavekit create-from-local \
  --server https://wavekit.example \
  --owner-profile-ref wavekit:user:ACCOUNT_UUID \
  --operation-key owner:create-new:001 \
  --lineage-visibility preserved \
  --preview-token TOKEN --confirm \
  --root ../independent-project --format json
```

Use `private` for private lineage or `dropped` when no lineage was retained.
This creates a new remote authority; it does not reattach the project to the
old source.

## Immutable Project Publication

Publication uploads an exact canonical bundle and records immutable/versioned
metadata only after the server echoes matching project, revision and digest
evidence. The live binding is compared before and after the operation.

```bash
p2p wavekit lifecycle preview publish-copy \
  --operation-id owner:publish-copy:001 --root . --format json
p2p wavekit publish-copy \
  --operation-id owner:publish-copy:001 --preview-token TOKEN \
  --confirm --root . --format json
```

This project-snapshot publication is unrelated to domain or vertical catalog
publication. It cannot become a live project without a separate create flow.

## Archive, Restore And Remote Delete

Archive preserves remote identity and history while making linked replicas
non-writable. Restore is a server-authorized forward transition followed by
local catch-up; it is not a local rewind.

```bash
p2p wavekit lifecycle preview archive \
  --operation-id owner:archive:001 --root . --format json
p2p wavekit archive \
  --operation-id owner:archive:001 --preview-token TOKEN \
  --confirm --root . --format json

p2p wavekit lifecycle preview restore \
  --operation-id owner:restore:001 --root . --format json
p2p wavekit restore \
  --operation-id owner:restore:001 --preview-token TOKEN \
  --confirm --root . --format json
```

Remote delete is a confirmed, idempotent server operation that first enters the
server's retention/tombstone lifecycle. If local state must survive, complete a
verified independent detach first and provide that project as evidence:

```bash
p2p wavekit lifecycle preview delete-remote \
  --operation-id owner:delete:001 --keep-local --root . --format json
p2p wavekit delete-remote \
  --operation-id owner:delete:001 --preview-token TOKEN \
  --keep-local --detached-root ../independent-project \
  --confirm --root . --format json
```

P2P rejects `--keep-local` unless the target contains a verified detach receipt
matching the exact source UUID and remote project. A tombstone received later
blocks mutation and never converts an old replica to standalone mode.

## Remove One Local Replica

Local removal first catches up, verifies no drift or unresolved recovery,
deactivates only this replica registration and then applies the explicit local
disposition. It does not archive or delete the WaveKit project.

```bash
p2p wavekit lifecycle preview remove-local-replica \
  --operation-id owner:remove-replica:001 --root . --format json
p2p wavekit remove-local-replica \
  --operation-id owner:remove-replica:001 --preview-token TOKEN \
  --disposition archive --archive-to /safe/new/archive-location \
  --integration remove --confirm --root . --format json
```

`--disposition remove` permanently removes `.p2p`; archive moves it to a new,
external path. `--integration remove` removes only unchanged P2P-owned host
integration artifacts and blocks on user-modified content. A project that is
then accessed as `remote-only` uses authenticated WaveKit web, API or MCP HTTP
instructions. That access mode has no local P2P profile or generated files, so
it is not selected through the local integration CLI.

## Recovery And MCP Boundary

For a lost or unknown response, inspect and recover the same operation:

```bash
p2p wavekit lifecycle recover owner:suspend:001 --root . --format json
```

Local MCP exposes only:

- `p2p_project_lifecycle_status`;
- `p2p_project_lifecycle_preview`;
- `p2p_project_publication_list`.

They are read-only and cannot confirm lifecycle changes. There is deliberately
no MCP apply, detach, create-from-local, publish, remote-delete or local-removal
tool. Generated agent instructions carry this same restriction.

Lifecycle payloads never contain credentials. Authentication secrets remain in
the operating-system credential store, and endpoint templates must stay on the
advertising server's origin.
