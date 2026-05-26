# Suggested Scope - PROP-016

## Include

- Define `.p2p/registries/` as the generated registry layer for P2P Engine.
- Define typed registry files:
  - `proposals.yml`
  - `decisions.yml`
  - `changes.yml`
  - `choices.yml`
  - `relations.yml`
  - `artifacts.yml`
- Define the registry source-of-truth rule:
  - primary sources remain `.p2p/proposals/`, `.p2p/decisions/`, `.p2p/choices/`, `.p2p/changes/` and governance/project artifacts.
  - registries are derived, deterministic and regenerable.
- Add CLI commands:
  - `p2p registry refresh`
  - `p2p registry status`
  - `p2p registry show proposals`
  - `p2p registry show changes`
- Use registries as compact context for:
  - proposal intake
  - overlap analysis
  - conflict checks
  - project refresh
  - future exporters
  - AI-guided navigation

## Exclude

- Database or server-side registry storage.
- Full graph database semantics.
- Manual registry editing workflow.
- Automatic Git commits or branch operations.
- Replacing `.p2p/project/` with registries.
- Complete OpenSpec or Spec Kit export implementation.

## Proposed Structure

```text
.p2p/
  registries/
    proposals.yml
    decisions.yml
    changes.yml
    choices.yml
    relations.yml
    artifacts.yml
```

## Minimum Registry Shape

### `proposals.yml`

```yaml
generated: true
proposals:
  - id: PROP-016
    title: Project Registries MVP
    status: draft
    path: .p2p/proposals/PROP-016-project-registries-mvp
    related_changes: []
    related_decisions: []
```

### `changes.yml`

```yaml
generated: true
changes:
  - id: CHANGE-001
    title: Managed Git Adapter and Change Set Model
    status: planned
    path: .p2p/changes/CHANGE-001-managed-git-adapter-and-change-set-model
    included_proposals:
      - PROP-013
      - PROP-014
      - PROP-015
```

### `relations.yml`

```yaml
generated: true
relations:
  - source: PROP-016
    target: PROP-010
    type: extends
    rationale: Registries extend the project state model with global indexes.
```

## Completion Boundary

The MVP is complete when P2P can regenerate registries from existing `.p2p/` artifacts and show a readable status without treating registry files as primary sources.
