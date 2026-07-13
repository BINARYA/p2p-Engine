# Recommendation - INTAKE-003

Classification: new architectural concern with strong overlap.

The idea is valid and should be preserved as a future architecture proposal. The concurrency issue observed during local proposal/artifact work is a small version of the same class of problem that becomes more serious with multiple people, multiple agents, remote branches, and cloud runners.

Existing accepted work already recognizes part of the problem:

- `PROP-013` keeps Git as the internal persistence, audit, synchronization, and collaboration layer.
- `PROP-030` introduces P2P Work as the user-facing abstraction over managed Git branches.
- `PROP-072` defines concurrent managed collaboration and explicitly treats fetch/scan/recheck/renumber as sufficient for MVP but not as a perfect distributed lock.
- `PROP-076` assigns hosted database, queues, permissions, jobs, and multi-tenant concerns to future P2P Cloud, not to the local P2P Engine runtime.

The new concern is not simply "replace files with a DB". The more durable architectural move is to separate P2P memory semantics from the physical storage backend:

```text
P2P memory model / transactions / identity / locks / invariants
-> storage adapter
-> filesystem+Git backend for local projects
-> structured DB backend for coordinated remote/cloud collaboration
```

This keeps the current Git-native audit model intact while making room for a structured persistence layer where concurrent writes, transactions, id allocation, locks, event ordering, and multi-user coordination require stronger guarantees than loose filesystem writes.

Primary next action: create a dedicated proposal for a P2P persistence boundary and concurrency-safe memory model. It should not immediately mandate a database. It should define the boundary, invariants, backend options, migration path, and compatibility constraints first.

Recommended title: `Structured Persistence Boundary and Concurrency-Safe Memory Model`.
