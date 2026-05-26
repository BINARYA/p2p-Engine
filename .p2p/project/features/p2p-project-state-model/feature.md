# P2P Project State Model

## Provenance

- Proposal: PROP-010
- Source: .p2p/proposals/PROP-010-p2p-software-specification-model

## Problem

Accepted P2P proposals are not yet transformed into a single rationalized project state that can guide implementation, feature tracking, task planning, or downstream export.

## Proposal

Add a P2P project state model that turns accepted proposals into versioned project artifacts under `.p2p/project/`. The MVP uses explicit refresh via `p2p project refresh`; automatic refresh after acceptance can be added later.

## Decision

# Decision - PROP-010

## Status

`accepted`

## Outcome

accepted

## Reason

P2P Engine needs an internal rationalized project state before exporting to OpenSpec, Spec Kit, or task systems. Raw proposal folders contain discussion, governance, alternatives, and decision history; they should not be treated directly as implementation specifications.

## Decision

Create a versioned `.p2p/project/` layer.

The official `.p2p/project/` state lives on `main`. Proposal branches may contain preview changes. When a proposal is accepted and merged, the corresponding project-state changes become official.

## Initial Model

```text
.p2p/project/
  overview.md
  problem.md
  scope.md
  project-swot.md
  features/
    <feature-id>/
      feature.md
      tasks.yml
      actions.yml
  decisions-map.yml
  conflicts.yml
  exports/
    markdown/
    openspec/
    speckit/
```

## Refresh Policy

The MVP uses explicit refresh:

```bash
p2p project refresh
```

Automatic refresh after accepted decisions can be added later as an opt-in behavior.
