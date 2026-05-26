# Suggested Scope - PROP-012

## Include

- Add `p2p impact prompt PROP-XXX`.
- Add `p2p impact import PROP-XXX <file-or-dir>`.
- Add proposal artifacts:
  - `impact-map.yml`
  - `related-proposals.yml`
  - `conflict-analysis.yml`
- Add `p2p conflict record`.
- Add `p2p conflict status`.
- Store persistent conflicts in `.p2p/project/conflicts.yml`.

## Exclude

- Automatic AI invocation.
- Automatic proposal rejection.
- Complex graph visualization.
- Merge conflict resolution.

## Suggested Artifact Shape

```yaml
impact:
  proposal: PROP-012
  features:
    - project-refresh-mvp
  commands:
    - p2p project refresh
  files:
    - .p2p/project/conflicts.yml
  dependencies:
    - PROP-010
    - PROP-011
  risks:
    - conflict detection may be advisory only
```
