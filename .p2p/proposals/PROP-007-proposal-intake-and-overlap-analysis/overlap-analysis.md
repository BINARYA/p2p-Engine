# Overlap Analysis - PROP-007

## Purpose

Define how P2P Engine should evaluate a rough idea against existing proposals before creating new work.

## Example Input

```text
preparare una CLI con dei comandi definiti
```

## Example Result

| Proposal | Overlap | Reason |
|---|---|---|
| PROP-001 - CLI Foundation | high | Covers CLI foundation and command skeleton |
| PROP-004 - Prompt-only Import Workflow | medium | Covers specific prompt/import commands |
| PROP-002 - Exploration Phase | low | Covers exploration workflow, not CLI commands directly |

## Suggested Action

```yaml
action: add_contribution
target: PROP-001
reason: The idea is mainly covered by CLI Foundation but can enrich its command scope.
next_command: p2p contribution add PROP-001 "preparare una CLI con dei comandi definiti" --type suggestion --relevance high
```

