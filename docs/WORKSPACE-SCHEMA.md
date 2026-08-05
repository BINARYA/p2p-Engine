# Current Workspace Schema Contract

P2P Engine 0.4.9 supports workspace schema 3 only. Fresh `p2p init` operations
create that schema and its complete canonical layout.

Inspect the contract without writing:

```bash
p2p workspace schema status
p2p workspace schema status --format json
```

The status is writable only when `layout_status` is `current` and
`current_version` is `3`. A missing declaration, schema 1 or 2, an unknown
contract, or a future schema returns `P2P_WORKSPACE_UNSUPPORTED_SCHEMA`.
P2P Engine 0.4.9 does not plan or apply workspace conversions.

The current workspace declaration contains only the current contract,
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

Do not edit schema declarations, locks, journals, originals, or candidates by
hand. Transaction recovery is CLI-only; MCP exposes read-only workspace schema
status.

After initialization or recovery, run:

```bash
p2p validate
p2p workspace schema status --format json
```
