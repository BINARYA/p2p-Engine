# Board Game Project Example

This example shows that P2P Engine is not limited to software projects.

It demonstrates:

- a board-game-domain P2P workspace;
- one accepted proposal;
- one Change Set derived from that accepted proposal;
- generated registries and readiness assessment;
- Codex-oriented agent boundary files.

## Scenario

The project needs a first playable loop before expanding rules, components, or
balance:

```text
Prototype a cooperative tile-placement game where players connect three shrines
before the storm deck runs out.
```

## What To Inspect

```bash
p2p proposal show PROP-001 --root examples/board-game-project
p2p change show CHANGE-001 --root examples/board-game-project
p2p context --budget small --root examples/board-game-project
p2p validate --root examples/board-game-project
```

## Artifact Map

```text
.p2p/
  project.yml
  project/
    assessment.yml
    rubrics.yml
  proposals/
    PROP-001-prototype-cooperative-tile-game/
  changes/
    CHANGE-001-prototype-cooperative-tile-game/
  registries/
```

## Why This Example Exists

P2P Engine is a project-governance engine, not only a software spec tool. This
example uses the same chain for a game design project:

```text
rough idea -> proposal -> accepted decision -> Change Set -> agent context
```
