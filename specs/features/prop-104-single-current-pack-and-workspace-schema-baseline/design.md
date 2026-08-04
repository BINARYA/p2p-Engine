# Design - Single Current Pack And Workspace Schema Baseline

## Decision Summary

P2P Engine 0.4.6 has one runtime baseline:

```text
workspace schema:       3
vertical pack schema:   2
portable package format: 1
```

These values describe separate contracts and must remain separately named in
code and machine output. Compatibility code is removed rather than hidden
behind an option.

## Compatibility Inventory

The implementation starts with a searchable inventory covering:

- schema defaults and `{1, 2}` branches in vertical models/loaders;
- bundled manifests and vertical definitions;
- bare-ID/project-local precedence branches that exist only for schema 1;
- workspace schema-v2 readers, migration plans and generated guidance;
- test fixtures and docs that assert obsolete behavior;
- MCP and release-package tests that embed old resources.

Each inventory item is either converted, deleted, or retained with a reason
unrelated to compatibility. Numeric schema fields belonging to other domain
artifacts are not part of this cleanup.

## Vertical Resource Conversion

All resources under `src/p2p_engine/resources/verticals/` become canonical
schema-2 directories. Built-in ownership uses publisher `binarya`; existing IDs
are retained and versions start at the exact release selected during
conversion. Dependencies and `extends` use exact coordinates and semantic
checksums.

The semantic content of sections, fields, rubrics, profiles, modules and
artifacts is retained. Conversion must not silently add placeholder sections.
The loader validates schema 2 before composition, irrespective of whether the
pack came from bundled resources, project-local installation or user cache.

## Workspace Baseline

`WorkspaceSchemaService` accepts only a valid schema contract whose current
version is 3. Mutation entry points call the existing runtime/schema preflight
before writing. Old migration modules may be retained only as an unshipped
development script long enough to convert the canonical project; they are not
reachable from normal CLI or MCP runtime.

The canonical project conversion uses a copy-first workflow:

1. inventory semantic state at the source commit;
2. convert into a fresh temporary root;
3. refresh registries and projections using public commands;
4. validate and compare semantic evidence;
5. replace the canonical root only through an explicit owner-controlled
   repository operation;
6. delete the disposable converter after evidence is recorded.

If the canonical project already declares schema 3, no workspace conversion is
performed; only pack/resource conversion evidence is required.

The durable atomic writer is retained because it protects current-schema
mutations, not because it converts schemas. Its lock, journal and recovery
surface use workspace-transaction terminology and live under
`.p2p/.internal/workspace-transactions/`.

## Error Contract

Core/service exceptions carry stable codes and structured details. CLI JSON
adapts them through the common envelope defined by `PROP-107`; text mode emits
the code, problem and recovery action. Unsupported layouts are never guessed
from missing values.

## Module Ownership

- `core/project_verticals.py`: current pack constants and typed schema-2
  models.
- `services/project_verticals.py`: single load/compose/resolve path.
- `services/workspace_schema.py`: current-only workspace preflight.
- `resources/verticals/`: converted canonical packs.
- `scripts/`: temporary conversion/audit utility when required; never package
  data.
- `tests/`: current-contract fixtures and rejection tests.

## MCP Decision

No new MCP tool is added. Existing MCP calls use the same workspace facade and
therefore receive the same unsupported-schema failure. MCP contract tests must
prove that no alternate legacy reader remains reachable.

## Rollout

1. Convert packaged resources and lock their checksums in tests.
2. Switch vertical parsing and resolution to schema 2 only.
3. switch workspace preflight to schema 3 only.
4. Remove obsolete runtime code, fixtures and guidance.
5. Run source-tree and wheel checks.
6. Publish 0.4.6 and update WaveKit's worker pin in a separate repository
   change.
