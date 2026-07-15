# Workspace Schema And Migration

P2P Engine versions the governed workspace layout independently from the
runtime compatibility contract. Runtime compatibility answers which engine can
operate the project. Workspace schema status answers which artifact layout is
present and whether semantic alignment still needs owner input or curation.

## Inspect

All inspection and planning commands are read-only:

```bash
p2p workspace schema status
p2p workspace schema status --format json
p2p workspace migrate plan --to 1
p2p workspace migrate plan --to 1 --input migration-input.yml --format json
p2p project progress --format json
p2p project freshness --format json
p2p validate
```

`legacy_undeclared` is inspectable. It does not mean that Markdown or YAML data
is invalid. `layout_status` and `alignment_status` are separate: a current
layout can remain degraded while owner decisions, historical relation curation
or derived rebuilds are outstanding.

## Owner Input

The migration planner never chooses a vertical, owner identity or project
metadata. Supply reviewed values in a narrow patch:

```yaml
vertical:
  id: software_project
  profile: default
  modules: []
  rubric_mapping: {}
owner:
  id: owner
  name: Project Owner
metadata:
  status: active
  workflow_phase: delivery
  current_objective: Complete the current implementation slice.
```

Omit values that should not change. Unknown fields and unsafe path-like values
are rejected. A plan can remain useful while reporting owner-input or
repository-curation blockers, but it cannot be applied until they are resolved.

## Apply

Review the complete JSON plan and retain its semantic fingerprint. Apply must
receive the same target and owner input again:

```bash
p2p workspace migrate apply \
  --to 1 \
  --input migration-input.yml \
  --plan-fingerprint '<reviewed-fingerprint>' \
  --actor owner \
  --confirm
```

Apply recomputes the plan before and after acquiring an exclusive process-safe
lock. It stages all candidates, validates the candidate overlay, snapshots
original bytes, replaces the workspace schema last and rolls handled failures
back in reverse order. It does not require Git or network access.

Do not edit `.p2p/project/workspace-schema.yml`, transaction locks or candidate
files manually. An incompatible exact runtime contract must be updated first
through `p2p runtime contract preview` and `apply`; that update is itself an
atomic multi-file operation.

## Recovery

An interrupted migration blocks unrelated governed writes and is visible in
`status`, `doctor`, compact context, validation and `next`.

```bash
p2p workspace migrate recovery status --format json
p2p workspace migrate recovery resume \
  --transaction-id migration-... --actor owner --confirm
p2p workspace migrate recovery rollback \
  --transaction-id migration-... --actor owner --confirm
```

Resume succeeds only while journal, candidates and current target hashes match
exact preconditions. Rollback restores only targets still containing the exact
candidate bytes written by the transaction. An external edit is preserved and
keeps recovery state visible instead of being overwritten.

## After Migration

Canonical changes make downstream nodes stale; they do not silently mark
generated or curated material current. Follow the ordered plan from:

```bash
p2p project freshness
```

Deterministic commands can be run in order. Stop before `agent_curated` or
`owner_review` stages. Refreshing registries and project projections reconciles
only declared generated outputs and preserves unknown/manual directories.

Migration apply, rollback and resume are CLI-only in schema v1. MCP exposes
read-only schema status, migration plan, progress, freshness and vertical
coverage show/suggest tools.
