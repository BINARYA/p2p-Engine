# Minimal Software Project Example

This example shows a small software project managed with P2P Engine.

It demonstrates:

- a software-domain P2P workspace;
- one accepted proposal;
- one Change Set derived from that accepted proposal;
- generated registries and readiness assessment;
- Codex-oriented agent boundary files.

## Scenario

The project needs a small first feature that is useful enough to implement and
simple enough to review:

```text
Build a local CLI task tracker with add, list, complete, and export commands.
```

## What To Inspect

```bash
p2p proposal show PROP-001 --root examples/minimal-software-project
p2p change show CHANGE-001 --root examples/minimal-software-project
p2p context --budget small --root examples/minimal-software-project
p2p validate --root examples/minimal-software-project
```

## Artifact Map

```text
.p2p/
  project.yml
  project/
    assessment.yml
    rubrics.yml
  proposals/
    PROP-001-start-with-cli-task-tracker/
  changes/
    CHANGE-001-start-with-cli-task-tracker/
  registries/
```

## Why This Example Exists

This is the smallest software-shaped flow:

```text
rough idea -> proposal -> accepted decision -> Change Set -> agent context
```

It is meant for readers who want to understand the value of P2P Engine before
looking at the full CLI or MCP references.
