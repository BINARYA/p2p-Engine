# Suggested Scope - PROP-010

## Include

- Define `.p2p/project/` as the home for rationalized generated project state.
- Define minimal project files:
  - `overview.md`
  - `problem.md`
  - `scope.md`
  - `project-swot.md`
  - `features/<feature-id>/feature.md`
  - `features/<feature-id>/tasks.yml`
  - `features/<feature-id>/actions.yml`
  - `decisions-map.yml`
  - `conflicts.yml`
- Define explicit refresh command:
  - `p2p project refresh`
- Define later automatic refresh behavior after accepted decisions.
- Define provenance from output sections back to accepted proposal IDs.

## Exclude

- Full OpenSpec exporter.
- Full Spec Kit exporter.
- AI-based automatic rewriting.
- Web UI for spec review.
- Complex schema validation.

## Suggested MVP Commands

```bash
p2p project refresh
p2p project status
p2p project show cli
```

## Suggested Later Commands

```bash
p2p project prompt PROP-010
p2p project import PROP-010 project-output.md
p2p export PROP-010 --target openspec
p2p export PROP-010 --target speckit
```
