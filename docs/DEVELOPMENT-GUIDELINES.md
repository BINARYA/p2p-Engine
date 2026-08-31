# P2P Engine Development Guidelines

This document supersedes the pre-0.5 modular-refactoring sequence. That
sequence included Git-owned runtime services that were deliberately removed
for the 0.5.0 clean boundary and is not an operational checklist.

## Repository Boundary

This repository owns P2P Engine implementation source, tests, packaging,
release automation and technical documentation. It does not own the canonical
P2P Engine project-design state. Governance commands must target the separate
`../projects/p2p-engine-project` root explicitly.

P2P Engine runtime owns structured project intent stored through the selected
local project-state adapter inside the `.p2p/` container. It does not own
repository synchronization, branches, commits, merge,
review requests, CI or publication. External repository tools may supply opaque
traceability references, which never prove implementation status.

## Change Shape

- Keep CLI and MCP presentation thin over shared services.
- Keep core models deterministic and presentation-free.
- Route governed writes through the existing preview/apply, authority,
  idempotency and receipt contracts.
- Preserve atomic complete-set writes for generated registries and other
  multi-file derived state.
- Route machine-readable CLI output through the shared raw JSON serializer.
- Reject duplicate YAML keys before portable-package canonicalization.
- Keep bundled and portable release state free of host-specific paths.
- Keep application/domain services storage-neutral; SQL, YAML paths and adapter
  journals remain inside adapters.
- Never implement backend comparison by dual-writing one project.
- Add the narrowest source, subprocess and installed-wheel regressions that
  prove a public contract.
- Do not reintroduce compatibility aliases or removed source-control surfaces.

## Required Checks

Use the repository scripts from the implementation checkout:

```bash
python scripts/generate-wavekit-transition-fixtures.py --check
python scripts/check-source-boundary.py
./scripts/check-static.sh
./scripts/test-public.sh -q
./scripts/test-full.sh -q
```

Release candidates additionally require owner-controlled metadata, reproducible
artifacts, standard package checks, dependency audit and the isolated installed
wheel harness. Coverage remains an optional diagnostic and is not part of the
0.5.1 candidate gate.
