# Binding Report - PROP-104 Through PROP-107 Vertical Platform 0.4.6

## Inputs

- Accepted P2P proposals: `PROP-104`, `PROP-105`, `PROP-106`, `PROP-107`.
- Owner decisions: accepted by `mrjungle` on 2026-08-03.
- Refreshed governed features:
  - `single-current-pack-and-workspace-schema-baseline`;
  - `local-vertical-catalog-and-remote-registry-client`;
  - `vertical-draft-authoring-derivation-and-publication-lifecycle`;
  - `versioned-cli-contract-and-idempotent-mutation-receipts`.
- Existing steering: `specs/steering/*`.
- Prior implementation contract:
  `specs/features/prop-103-portable-versioned-vertical-packs-and-governed-project-adoption/`.
- Source inspected: vertical models/services/resources, workspace schema and
  transactions, filesystem facade, CLI registration and project vertical
  commands.
- Tests inspected: portable verticals, project verticals, workspace schema,
  release artifacts, CLI and version consistency.

## Classification

### Steering Context

- P2P Engine owns deterministic pack schemas, authoring/materialization,
  local/remote client behavior and project-memory mutation.
- WaveKit owns server accounts, authorization, catalog policy, moderation,
  counters and serialized worker execution.
- The integration boundary remains the versioned P2P CLI and verified local
  artifacts; WaveKit does not write `.p2p` or canonical pack YAML directly.

### Feature Specs Created

- `specs/features/prop-104-single-current-pack-and-workspace-schema-baseline/`
- `specs/features/prop-105-local-vertical-catalog-and-remote-registry-client/`
- `specs/features/prop-106-vertical-draft-authoring-derivation-and-publication-lifecycle/`
- `specs/features/prop-107-versioned-cli-contract-and-idempotent-mutation-receipts/`

Each directory contains `requirements.md`, `design.md` and `tasks.md`.

### Current Implementation Focus

- Package version raised to 0.4.6.
- Four bundled packs converted to schema 2 and exact
  `binarya/<id>@2.0.0` coordinates.
- Initial `p2p-cli/v1` envelope and `p2p version` delivered.
- Initial top-level local `p2p vertical` list/inspect and registry
  add/list/remove delivered without remote network access.

### Open Gaps

- Schema-1 and pre-v3 runtime compatibility removal is not complete.
- Registry capability negotiation, keyring login, remote search/pull and
  immutable cache are not implemented.
- Draft normalized document, materialization, publication and proposal guard
  are not implemented.
- Global JSON conversion/parser normalization and mutation receipts are not
  implemented.

## Requirement-To-Evidence Matrix

| Source | Requirement Area | Evidence | Status | Notes |
| --- | --- | --- | --- | --- |
| PROP-104 | Bundled schema-2 resources | `src/p2p_engine/resources/verticals/*`, `tests/test_project_verticals.py` | implemented | All four exact packs package deterministically. |
| PROP-104 | Current-only workspace/pack runtime | feature task T002-T010 | open | Compatibility inventory and deletion are still required. |
| PROP-105 | User-root registry configuration | `services/vertical_registry.py`, `tests/test_vertical_registry.py` | implemented | No credentials or network calls. |
| PROP-105 | Remote auth/search/pull/cache | feature task T004-T014 | open | Must remain explicit and checksum-bound. |
| PROP-106 | Draft lifecycle | feature task T002-T016 | open | WaveKit normalized-document contract is not available yet. |
| PROP-107 | Version discovery | `cli.py`, `tests/test_cli_contract.py` | implemented | Source and wheel smoke verified. |
| PROP-107 | Uniform JSON and idempotent applies | feature task T002-T005, T008-T014 | open | Existing unconverted JSON shapes remain. |

## Task Completion Decisions

- Marked complete only tasks backed by source, tests and observed wheel/CLI
  behavior.
- Left partially implemented aggregate tasks unchecked even when one command
  in the group exists.
- Full suite evidence at this binding point: `1479 passed, 3 skipped`.
- Focused post-documentation evidence: `22 passed`, documentation checks
  `8 passed`, bundled/current CLI checks `12 passed`.
- Release artifact evidence: 0.4.6 wheel (`248` files), sdist (`502` files),
  installed-wheel version and four bundled schema-2 packs verified.

## Implementation Gaps

Continue in dependency order:

1. finish `PROP-104` current-only validation and compatibility deletion;
2. finish `PROP-107` envelope/parser base needed by every new command;
3. implement `PROP-105` secure registry transport/cache;
4. implement `PROP-106` draft and publication lifecycle;
5. add `PROP-107` atomic receipts to install/adopt/migrate apply;
6. update WaveKit fixtures and worker pin in its separate repository.

## Owner Questions

None. The accepted proposals and technical specs define the current direction;
remaining choices are implementation details constrained by those contracts.
