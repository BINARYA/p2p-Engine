# Current Workspace Schema Contract

P2P Engine 0.6.2 supports workspace schema 4 only. Fresh `p2p init` operations
create that schema and its complete canonical layout.

Inspect the contract without writing:

```bash
p2p status --format json
p2p workspace schema status
p2p workspace schema status --format json
```

`p2p status --format json` returns the workspace status beside the full release
`contract_versions` tuple shared with `p2p version --format json` and
`p2p_workspace_schema_status`.

The status is writable only when `layout_status` is `current` and
`current_version` is `4`. A missing declaration, schema 1, 2 or 3, an unknown
contract, or a future schema returns `P2P_WORKSPACE_UNSUPPORTED_SCHEMA`.
The runtime does not plan or apply workspace conversions.

Schema 4 requires `.p2p/project/authority.yml`, the portable classification in
`.p2p/project/domain.yml`, and independent initialization provenance in
`.p2p/project/structure-source.yml`. It also requires the canonical detached
aggregate in `.p2p/project/structure.yml` and append-only revision evidence in
`.p2p/project/structure-events.yml`. Current initialization also writes the
storage-neutral stable identity contract and local replica record described in
[`PROJECT-IDENTITY.md`](PROJECT-IDENTITY.md). Identity-less development state
must use explicit backup-protected adoption; malformed or contradictory
identity blocks governed mutations. A structural domain template is not a
valid schema-4 domain descriptor. `vertical.yml`, `vertical.lock.yml` and
`definition.yml` are optional transition/definition artifacts; they do not
replace project-structure authority.

The workspace schema is a physical adapter concern, not the interchange
contract. `p2p-canonical-memory/v1` projects the portable logical aggregate;
`p2p-project-bundle/v1` serializes it deterministically and never embeds a live
SQLite database, filesystem journal or WAL/SHM file. Replica-local state and
generated projections remain outside the semantic digest. See
[`CANONICAL-MEMORY-AND-BUNDLES.md`](CANONICAL-MEMORY-AND-BUNDLES.md).
Typed authority evidence is required for integrated governed mutations. See
[`AUTHORITY-CONTEXT.md`](AUTHORITY-CONTEXT.md). The current workspace declaration contains only the current contract,
initialization baseline, date and actor. Obsolete migration-history fields are
invalid and are never interpreted by the runtime.

## Atomic Transaction Recovery

Current-schema governed writes use an atomic journal under:

```text
.p2p/.internal/workspace-transactions/
```

This journal is transaction safety infrastructure, not schema migration
support. A handled failure rolls back automatically. If external edits prevent
automatic rollback, unrelated governed writes remain blocked until an owner
inspects and explicitly recovers the transaction:

```bash
p2p workspace transaction status --format json
p2p workspace transaction rollback <transaction-id> \
  --actor owner --confirm --format json
p2p workspace transaction resume <transaction-id> \
  --actor owner --confirm --format json
```

Rollback restores recorded preimages only when the live files still match the
transaction candidates. Resume verifies every replaced target, every pending
preimage, and every staged candidate before completing the commit. A mismatch
remains fail-closed for manual investigation.

Do not edit schema declarations, project structure, event ledgers, locks,
journals, originals, receipts or candidates by hand. Transaction recovery is
CLI-only; MCP exposes read-only workspace schema status.

After initialization or recovery, run:

```bash
p2p validate
p2p workspace schema status --format json
```
