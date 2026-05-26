# Software Spec - CHANGE-012 - P2P Software Spec Generator MVP

## Summary

CHANGE-012 introduces the P2P-native software specification layer for Change Sets. The MVP adds a `p2p spec` command group that can generate a deterministic specification from accepted P2P source artifacts, produce a refinement prompt for human or AI-assisted editing, validate a refined spec directory, and import the validated artifacts back into the P2P workspace.

The generated specification is implementation-facing but remains governed by P2P source of truth: accepted proposals, Change Sets, decisions, tasks, and provenance. It is intended to become the intermediate layer before future OpenSpec or Spec Kit export, without implementing those exporters in this Change Set.

## Source

- Change Set: `CHANGE-012`
- Change path: `.p2p/changes/CHANGE-012-p2p-software-spec-generator-mvp`
- Included proposals: `PROP-026`
- Accepted decisions: none recorded for this Change Set

## Targets

- execution_domains: `software`
- implementation_targets: `local_cli`
- spec_targets: `p2p_spec`
- export_targets: `openspec`, `speckit`

## Artifact Contract

Each generated or imported software spec for a Change Set must contain:

- `index.md`
- `requirements.md`
- `design.md`
- `commands.yml`
- `data-model.yml`
- `acceptance.md`
- `provenance.yml`

YAML artifacts must preserve the required top-level keys used by validation:

- `commands.yml`: `commands`
- `data-model.yml`: `entities`
- `provenance.yml`: `source`

## Boundary

This MVP does not invoke AI directly, does not export to OpenSpec or Spec Kit, and does not create Git commits, branches, tags, or merges.
