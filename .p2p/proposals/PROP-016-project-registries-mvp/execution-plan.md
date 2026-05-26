# Execution Plan - PROP-016

## Objective

Introduce a generated registry layer that indexes the main P2P artifacts without replacing them as the source of truth.

## Workstream 1 - Registry Model

Define the registry folder and file layout:

```text
.p2p/registries/
  proposals.yml
  decisions.yml
  changes.yml
  choices.yml
  relations.yml
  artifacts.yml
```

Define the first compact schema for each registry. The schema should favor stable IDs, status, path, relationships and source artifact references over verbose narrative content.

## Workstream 2 - Registry Refresh

Implement `p2p registry refresh`.

The command should:

1. scan source artifacts under `.p2p/`;
2. collect proposal, decision, change, choice, relation and artifact metadata;
3. write deterministic YAML files under `.p2p/registries/`;
4. mark generated files with a header or metadata flag;
5. avoid changing Git state directly.

## Workstream 3 - Registry Status and Read Views

Implement:

```bash
p2p registry status
p2p registry show proposals
p2p registry show changes
```

The status command should detect whether registry files exist and whether core counts match the current artifact set.

The show commands should provide compact terminal views suitable for humans and AI agents.

## Workstream 4 - Integration Points

Prepare registries to support:

- `p2p project refresh`
- proposal intake and overlap analysis
- conflict memory
- Change Set creation
- future exporter inputs
- Codex/agent context loading

For MVP, integration can remain loose: registry commands may exist independently before other commands depend on them.

## Workstream 5 - Documentation and Tests

Update README and tests to show:

- why registries are generated;
- which files are primary sources;
- how to refresh and inspect registries;
- what manual editing policy applies.

## Acceptance Checks

- Running `p2p registry refresh` creates `.p2p/registries/`.
- Registries include current proposals and change sets.
- Running refresh twice produces stable output when sources have not changed.
- `p2p registry status` reports missing/stale/available registry files.
- `p2p registry show proposals` and `p2p registry show changes` are readable.
- No Git writes are performed by registry commands.
