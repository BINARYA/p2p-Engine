# Open Questions

No unresolved owner questions remain for the current proposal definition.

## Resolved Owner Inputs

- The visible generated output root is `outputs/`, not `project/`.
- The default export destination is fixed for the MVP and is not configurable.
- The canonical default document is `outputs/latest/project.md`.
- The default export is a single chaptered Markdown document.
- Specialized vertical exports are nested under `outputs/latest/exports/<profile-or-vertical>/`.
- Software-specific exports are profile outputs and are not the default representation.
- Existing `.p2p/outputs` artifacts must be treated as a compatibility surface and checked before removal.

## Implementation Decisions Deferred To Design

- Exact CLI command naming for generating the visible project definition.
- Exact renderer/service class layout.
- Whether legacy `.p2p/outputs` is mirrored, deprecated, migrated, or kept unchanged after compatibility analysis.
- Retention policy for old `outputs/review-###/` snapshots beyond deterministic creation.
