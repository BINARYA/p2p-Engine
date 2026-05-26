# Acceptance

## Criteria

- `p2p spec export --change CHANGE-XXX --target generic` writes a generic export bundle from an existing P2P software spec.
- `p2p spec export --change CHANGE-XXX --target openspec` writes an OpenSpec-oriented bundle from an existing P2P software spec.
- `p2p spec export-status` lists generated export bundles.
- `p2p spec export-show CHANGE-XXX --target TARGET` prints the export index.
- Unsupported export targets fail explicitly instead of silently generating an undefined format.
- Tests cover successful generic/OpenSpec export, export status/show, and unsupported targets.

## Tests / Verification

- T001: Export generic software spec bundle (completed)
- T002: Export OpenSpec-oriented software spec bundle (completed)
- T003: Inspect software spec export bundles (completed)
- T004: Reject unsupported export targets (completed)
- T005: Update P2P skill and tests (completed)
