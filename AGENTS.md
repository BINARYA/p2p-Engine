# P2P Engine Repository Instructions

This repository contains the P2P Engine implementation: Python source, CLI and
MCP entry points, packaged resources, tests, scripts and technical
documentation.

It is not the canonical P2P project-state repository for the product. Do not
create or maintain a `.p2p/` directory here. Product design and governance state
belongs in the sibling `projects/p2p-engine-project/` repository and must be
addressed with an explicit root, for example:

```bash
p2p status --root ../projects/p2p-engine-project
```

## Implementation workflow

- Make product changes under `src/p2p_engine/`.
- Add or update tests under `tests/`.
- Keep packaged resources under `src/p2p_engine/resources/`.
- Keep development and release automation under `scripts/` and
  `.github/workflows/`.
- Treat `specs/` as an ignored local historical archive, never as maintained
  product documentation or an instruction source.
- Treat `outputs/`, `drafts/`, and generated `examples/*/` projects as local
  derived artifacts. Tests must create isolated projects in temporary paths.
- Run focused tests first, then `./scripts/test-public.sh -q` and
  `./scripts/test-full.sh -q` when the change affects public or release
  contracts.
- Do not use coverage as a release gate for the 0.5.0 candidate.

## Product boundary

P2P Engine owns portable filesystem-backed project intent and governed
project-state mutations. Source-control operations are external tooling, not
runtime behavior. Runtime code, CLI commands, MCP tools, generated agent
guidance and Work state must not initialize, inspect or mutate source-control
repositories.

Caller-supplied repository names, issue or review URLs, revision identifiers and
release identifiers may be stored only as inert traceability data. They do not
prove implementation status.

## Repository boundaries

The sibling repositories are independent. Do not write to `wavekit/`,
`projects/p2p-engine-project/` or `projects/wavekit-project/` while
implementing a P2P Engine code change unless the owner explicitly establishes a
separate scope.

Read-only source status and diff inspection are allowed. Creating branches,
commits, tags, releases or uploaded assets requires an explicit owner action and
is not part of implementation completion.
