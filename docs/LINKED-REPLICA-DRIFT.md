# Linked Replica Drift And Recovery

A `linked-local` project is a local materialization of WaveKit authority. P2P
Engine verifies its logical identity, authority epoch, confirmed revision,
change-batch evidence, canonical semantic digest and blob-manifest digest. It
does not compare Git state, YAML formatting, filesystem timestamps, SQLite
pages, journals or WAL bytes.

## Classification

| Classification | Meaning | Write behavior |
| --- | --- | --- |
| `transient-valid` | Logical state matches confirmed evidence | allowed |
| `stale-valid` | Valid replica is behind WaveKit | catch-up allowed |
| `semantic-drift` | Decodable logical state differs | blocked |
| `identity-mismatch` | Project, replica or authority identity differs | blocked |
| `structural-corruption` | The adapter cannot prove integrity | blocked |
| `incomplete-local-operation` | A local activation/recovery is incomplete | blocked |

Adapter-owned transient state and formatting-only changes do not create a
false project drift. Before linked catch-up or mutation, P2P runs the same
integrity gate and fails before contacting WaveKit when the replica is blocked.

## Inspect Without Mutating

```bash
p2p drift status --root . --format json
p2p drift verify --root . --format json
p2p drift diff --root . --limit 256 --format json
p2p drift report --root . --format json
```

`status` and `diff` are also available through the read-only MCP tools
`p2p_replica_drift_status` and `p2p_replica_drift_diff`. Findings contain
logical entity identifiers and bounded digests, not physical paths or suspect
payloads. A corrupt replica returns an explicitly incomplete diff.

## Preserve And Rebuild

The default recovery is to preserve the suspect container, download a complete
verified WaveKit snapshot and blobs into staging, and atomically activate that
snapshot:

```bash
p2p drift backup --root . --format json
p2p drift discard --root . --confirm --format json
```

The forensic archive lives outside `.p2p` under the project-local
`.p2p-forensics/` recovery area. Public output exposes only an opaque backup
reference, digest and counts. P2P never uploads this archive or the suspect
YAML/database bytes. Rebuild preserves the registered replica identity and
resets its local feed evidence to the authoritative snapshot.

## Restate Recognized Intent

When the complete diff represents exactly one supported domain change, P2P can
produce a typed plan:

```bash
p2p reconcile preview --root . --format json
p2p reconcile apply --root . --plan-digest sha256:<digest> --confirm --format json
```

The first release translates only `project.domain.set` and
`project.domain.clear`. Every other difference remains explicitly unsupported.
WaveKit binds preview to the exact plan, rechecks owner capability and current
revision, and applies it through the ordinary durable command/receipt/feed
path. Before submission, P2P preserves the suspect state and rebuilds the local
replica from authority. A persisted apply marker makes retry after a lost
response idempotent without creating another backup or a second write path.

Rebuild and reconciliation apply are owner CLI operations. Local MCP and the
WaveKit web UI can inspect health and sanitized differences, but cannot repair,
discard or apply them.

## Standalone And Git Boundaries

Standalone projects use `p2p project memory backup`, restore preview/apply and
workspace recovery. They are not reported to WaveKit. If external tools or Git
change `.p2p`, P2P reacts only to the resulting logical state; it never reads
branches or commits and never uses Git merge as replica reconciliation. To
preserve an altered project as independent state, use the normal verified
derive/detach lifecycle so it receives its own project UUID.
