# Compatibility Inventory - PROP-104

## Converted

| Surface | Current result | Reason |
| --- | --- | --- |
| Four bundled vertical resources | Canonical schema-2 directories at exact `binarya/*@2.0.0` coordinates | Preserve maintained domain content on the only supported pack contract. |
| Canonical P2P Engine project active vertical | `binarya/software_project@2.0.0` with schema-2 lock | Keep the governed project usable by 0.4.6. |
| Canonical project workspace | Workspace schema 3, current and aligned | Keep project memory on the sole runtime contract. |
| Vertical and workspace tests | Current fixtures plus explicit rejection fixtures | Test supported behavior and fail-closed boundaries. |
| Agent templates and public docs | Current-only commands and recovery guidance | Prevent agents from invoking removed surfaces. |
| Release verifier | Current schema/transaction members | Ensure deleted compatibility modules cannot be required by release packaging. |

## Deleted

| Surface | Removed members |
| --- | --- |
| Workspace conversion runtime | `workspace_compatibility.py`, `workspace_migrations.py`, `workspace_migration_registry.py`, `workspace_migration_handlers.py` |
| Workspace conversion CLI | `cli_commands/workspace_migrations.py` and the `workspace migrate` command tree |
| Workspace conversion MCP | `p2p_workspace_migration_plan`; no migration apply/recovery MCP tools exist |
| Schema-1 vertical convenience flow | `project vertical propose`, `project vertical add`, their facade methods, models and MCP tools |
| Legacy pack loading | Flat `vertical.yml`, `vertical_candidate` normalization, schema defaults and source-precedence selection |
| Legacy conversion tests | CLI, compatibility-service, migration-service, v2 and v3 migration suites and shared legacy fixture |
| Obsolete guide | `docs/WORKSPACE-MIGRATION.md` |

## Retained Deliberately

| Surface | Reason unrelated to runtime compatibility |
| --- | --- |
| `workspace_schema.applied_migrations` | Inert historical audit already present in a current schema-3 workspace; no retired handler is loaded. |
| `AtomicMutationWriter` journal | Required for rollback-safe current-schema governed writes. It is now named workspace transaction infrastructure and stored under `.p2p/.internal/workspace-transactions/`. |
| CLI transaction status/rollback/resume | Provides an explicit owner-authorized recovery path when external edits prevent automatic rollback. |
| Runtime-contract adoption | Manages `.p2p/project/runtime.yml`, not workspace schema conversion. It remains gated by a current workspace when called through the facade. |
| Proposal legacy-authority resolution | Resolves decision evidence inside a schema-3 ledger; it is not a pre-v3 workspace reader. |
| Bare vertical IDs | Convenience lookup only when one exact coordinate exists; ambiguity and coordinate conflicts fail closed. |
| Other `schema_version: 1` artifacts | Independent domain contracts such as patches, agent registry and publication metadata; outside PROP-104. |

## One-Time Conversion Boundary

The canonical project conversion used released 0.4.5 commands from a temporary
runtime under `/tmp`, operated first on a disposable project copy, and then
replayed through public CLI commands on the canonical project after validation.
No converter, fallback reader or manual `.p2p` mutation was added to the 0.4.6
runtime.
