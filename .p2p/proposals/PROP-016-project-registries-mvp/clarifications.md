# Clarifications - PROP-016

## 1. Registry Location

Registries should live under `.p2p/registries/`, not directly under `.p2p/project/`.

Reason:
`.p2p/project/` is the derived project state view, while registries are cross-cutting indexes over proposals, decisions, choices, changes, relations and artifacts. Keeping them separate avoids treating the project map as the only consumer of indexed state.

## 2. Git Versioning

Registries should be committed to Git by default.

Reason:
They are generated artifacts, but they are useful for audit, review, AI context loading and export reproducibility. Since they are derived, they must remain deterministic and regenerable.

## 3. Refresh Command

The MVP should introduce a dedicated command:

```bash
p2p registry refresh
```

`p2p project refresh` may call `p2p registry refresh` later, but the registry lifecycle should remain visible and testable as a separate capability.

## 4. Minimum Fields

The first registry version should keep compact records:

- proposals: id, title, status, path, summary, source files, related changes, related decisions.
- decisions: id or proposal id, title, outcome, status, path, source proposal.
- changes: id, title, status, path, included proposals, referenced proposals, execution domains, task summary.
- choices: id, status, options, selected option, related proposals or decisions.
- relations: source, target, relation type, rationale, source artifact.
- artifacts: path, artifact type, owner entity, status, generated flag.

## 5. Manual Edits

Manual edits to registries should be considered unsupported.

For the MVP, refresh may overwrite registries. A generated-file header should make this explicit. Later, `p2p registry check` can detect drift and warn when generated files were manually changed.
