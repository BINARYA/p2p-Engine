# Exploration - PROP-016

## Interpretation

P2P Engine now has several source artifact families:

```text
.p2p/proposals/
.p2p/changes/
.p2p/project/
.p2p/governance/
```

The system can work by scanning folders, but as the project grows it needs explicit generated registries to support navigation, intake, overlap analysis, conflict detection, project refresh, and exporters.

## Core Principle

Registries are derived indexes, not the source of truth.

Primary sources remain:

```text
proposals
decisions
choices
changes
governance artifacts
project state
```

Registries make those sources queryable and easier to inspect.

## Suggested Structure

```text
.p2p/registries/
  proposals.yml
  decisions.yml
  changes.yml
  choices.yml
  relations.yml
  artifacts.yml
```

## MVP Commands

```bash
p2p registry refresh
p2p registry status
p2p registry show proposals
p2p registry show changes
```

## Why This Matters

Registries become the bridge between file-based artifacts and higher-level behavior:

- proposal intake can check existing proposals;
- impact analysis can find related artifacts;
- exporters can find accepted changes;
- project refresh can avoid ad hoc scanning logic;
- AI agents can load compact context instead of reading every file.
