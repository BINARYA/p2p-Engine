# Exploration - PROP-010

## Interpretation

PROP-010 introduces the missing bridge between P2P governance and software implementation. A P2P proposal is a decision artifact: it captures problem, context, discussion, alternatives, governance, and acceptance. It should not be exported directly to OpenSpec or Spec Kit as if it were already a clean software specification.

The project needs a rationalized output layer that turns accepted proposal decisions into stable implementation-facing artifacts.

## Core Insight

P2P Engine should own a neutral software specification model before exporting to downstream tools.

```text
proposal discussion
→ accepted decision
→ P2P software spec
→ implementation plan/tasks
→ optional OpenSpec/Spec Kit export
```

This keeps P2P Engine upstream and prevents OpenSpec or Spec Kit from becoming the source of truth.

## Proposed Project Layer

Use a dedicated rationalized project area:

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

The `project` directory contains rationalized derived artifacts. The source remains:

```text
.p2p/proposals/
.p2p/governance/
docs/
```

## Automatic Refresh

When a proposal is accepted, P2P Engine should be able to refresh derived outputs.

MVP behavior can be explicit:

```bash
p2p decision record PROP-010 --outcome accepted --reason "..."
p2p project refresh
```

Later behavior can be automatic:

```bash
p2p decision record PROP-010 --outcome accepted --reason "..."
# automatically refreshes .p2p/project/
```

The automatic behavior should be deterministic and file-based. It should not invoke AI by default; AI-assisted synthesis can remain a prompt/import workflow.

## Why This Matters

Without this layer, every exporter would need to understand the full history and ambiguity of P2P proposal artifacts. With this layer, exporters consume a stable normalized project model.
