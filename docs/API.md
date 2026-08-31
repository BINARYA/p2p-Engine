# Core API Reference

This document is the contributor-facing API reference for P2P Engine's Python core.

Status: preliminary contributor reference. End-user agents should prefer CLI and
MCP. Python API documentation is for contributors, future adapters, and
maintainers.

## Primary Facade

The current core facade is:

```python
from pathlib import Path

from p2p_engine.storage.filesystem import P2PWorkspace

workspace = P2PWorkspace(Path("."))
```

`P2PWorkspace` is retained as a thin compatibility facade. It opens the
storage-neutral `ProjectApplicationService`, which resolves one project adapter
and delegates current compatibility behavior to that adapter. New internal
consumers should depend on the application service or semantic ports rather
than importing filesystem implementations.

## Public Areas

Current method families include:

- project initialization and agent instructions;
- stable project identity/status, copy assessment, lifecycle DTOs, adoption and derivation;
- canonical-memory inventory/snapshot ports, deterministic bundle codec, physical backup and staged restore;
- status, validation, context, project-readiness v2, and maturity compatibility;
- proposals and contributions;
- decisions, votes, and precedents;
- choices and choice discovery;
- project state and operational brief;
- Change Sets;
- software specs and export;
- Work lifecycle;
- registries;
- conflicts and impact analysis.

## Example

```python
from pathlib import Path

from p2p_engine.storage.filesystem import P2PWorkspace

workspace = P2PWorkspace(Path("/path/to/project"))
proposal = workspace.create_proposal_with_details(
    title="Define onboarding",
    problem="New users need a clear setup flow.",
    goals=["Make init understandable."],
    proposal="Use a guided wizard.",
    acceptance_criteria=["A user can initialize a project without editing .p2p."],
)
print(proposal.proposal_id)
```

## Error Model

Most public methods raise `ValueError` for invalid IDs, missing source artifacts, invalid lifecycle transitions, or unsupported options.

Stable identity application services live in
`p2p_engine.services.project_identity`; typed storage-neutral values live in
`p2p_engine.core.project_identity`. Storage adapters implement the
`ProjectIdentityStore` port. End users should use the CLI/MCP surfaces documented
in [`PROJECT-IDENTITY.md`](PROJECT-IDENTITY.md), not adapter paths.

`CanonicalMemoryPort` is the backend-neutral read boundary used by
`CanonicalBundleCodec`. `FilesystemCanonicalMemoryStore` is the current
adapter. `CanonicalMemoryService` owns inspect/verify/export, coordinated or
closed-store backup, preview/apply restore, rollback and recovery status. These
Python types are contributor APIs; agents must use the CLI or explicit MCP
reads and must not inspect adapter-private storage. See
[`CANONICAL-MEMORY-AND-BUNDLES.md`](CANONICAL-MEMORY-AND-BUNDLES.md).

`ProjectStateRepository`, `ProjectUnitOfWork`, `BlobStore`, snapshot, backup and
migration ports live under `p2p_engine.ports.project_state`. Their DTOs and
normalized errors live in `p2p_engine.core.project_state_storage`. These are
internal contributor contracts, not a supported WaveKit integration API.
WaveKit and other server consumers continue to use the versioned CLI JSON
contract. See [`PROJECT-STORAGE-PORTS.md`](PROJECT-STORAGE-PORTS.md).

## Documentation Plan

This file should grow into:

- public method index;
- arguments, returns, and raised errors;
- examples for stable method families;
- notes on which methods are internal helpers despite being visible in Python;
- migration notes for later adapter implementations.

## Planned Additions

- proposal lifecycle API;
- choice API;
- Change Set API;
- Work API;
- assessment/readiness API;
- MCP/core mapping;
- adapter contract examples.
