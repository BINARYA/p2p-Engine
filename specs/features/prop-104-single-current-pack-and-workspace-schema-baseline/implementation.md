# Implementation Note - PROP-104

## Result

P2P Engine 0.4.6 now has one runtime baseline:

```text
workspace schema:         3
vertical-pack schema:     2
portable package format:  1
```

Unsupported pack and workspace contracts fail before governed mutation with
`P2P_VERTICAL_UNSUPPORTED_SCHEMA` or `P2P_WORKSPACE_UNSUPPORTED_SCHEMA`.
There is no shipped runtime conversion path.

## Canonical Project Evidence

The conversion was rehearsed on a disposable copy before the same public CLI
operations were applied to `projects/p2p-engine-project`.

| Evidence | Before | After |
| --- | ---: | ---: |
| Project-definition sections | 19 | 19 |
| Defined field values | 27 | 27 |
| Assumptions | 3 | 3 |
| Open project questions | 0 | 0 |
| Definition blockers | 0 | 0 |
| Enabled modules | 0 | 0 |
| Active vertical | legacy software reference | `binarya/software_project@2.0.0` |
| Workspace schema | 3 | 3 |
| Validation findings | 0 | 0 |

The migration preview reported no added or removed sections and no orphans.
The existing `applied_migrations` sequence remains historical audit data; the
0.4.6 runtime validates its structure without importing retired handlers.

## Bundled Pack Evidence

| Coordinate | Semantic checksum |
| --- | --- |
| `binarya/base_project@2.0.0` | `d53a537905b980ec40ae3df3be1c6e7a79a7ff6d98a6f09e91d79b2a582b5c88` |
| `binarya/software_project@2.0.0` | `15343e360996a1166fd32570d94d2e2c984076e5ad5f61f7af84355df3ee9e13` |
| `binarya/social_impact_program_design@2.0.0` | `9552f2c980a62566800a2423d79027ed69f285b2d3063b9f3517f7c4132f7c7b` |
| `binarya/packaging_or_physical_product_design@2.0.0` | `088c4d9cedcce08a3c8855732a454cb71197e02e286a9a506bd93f66a0b92831` |

Source and installed-wheel verification must reproduce these coordinates and
checksums and deterministic `.p2pv` bytes.

## Public Impact

- Removed CLI: `p2p workspace migrate ...`, `p2p project vertical propose`,
  and `p2p project vertical add`.
- Removed MCP: `p2p_workspace_migration_plan`,
  `p2p_project_vertical_propose`, and `p2p_project_vertical_add`.
- Retained current pack lifecycle: scaffold, inspect, validate, package,
  install preview/apply, adopt preview/apply and migrate preview/apply.
- Added current-write recovery: `p2p workspace transaction status|rollback|resume`.
- Exact coordinates are authoritative. Bare IDs are accepted only when one
  coordinate exists; semantic disagreement at one coordinate fails closed.

## Transaction Safety

The old schema migration engine was removed. The atomic writer was retained
because current proposal, decision, definition and vertical mutations need a
durable preimage/candidate journal. Its path and diagnostics were renamed from
workspace migration to workspace transaction terminology. Recovery verifies
live candidate hashes and pending preimages before rollback or resume, and
requires an owner when project permissions exist.

## WaveKit Impact

WaveKit must rebuild the P2P worker image against the 0.4.6 artifact. Disposable
development/test `.p2p` workspaces created by older schemas must be recreated.
WaveKit must use schema-2 `.p2pv` install/adopt/migrate calls and must not call
the removed candidate or workspace-migration surfaces. Production data rollout
and backward compatibility remain out of scope while no external projects use
the pre-release contracts.

## Verification

T013 closed with the following evidence:

- focused vertical-pack and portable-package group: 59 passed;
- combined high-risk schema, CLI and MCP group: 91 passed;
- documentation, decision, CLI, agent-template and release group: 41 passed;
- complete source suite: 1407 passed in 255.75 seconds;
- build outputs: `p2p_engine-0.4.6-py3-none-any.whl` and
  `p2p_engine-0.4.6.tar.gz`;
- release verifier: passed with 245 wheel files and 494 sdist files;
- isolated installed-wheel smoke: version 0.4.6, workspace schema 3,
  vertical-pack schema 2 and portable-package format 1;
- source and installed-wheel bundled coordinates and semantic checksums:
  identical for all four packs;
- canonical project validation: 0 errors, 0 warnings and 0 informational
  findings;
- canonical transaction status: no recovery required.
