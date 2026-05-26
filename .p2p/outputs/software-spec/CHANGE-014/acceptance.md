# Acceptance

## Criteria

- `p2p spec export --change CHANGE-XXX --target speckit` writes a Spec Kit-oriented feature directory.
- The feature directory includes `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, and `contracts/README.md`.
- Exported Spec Kit artifacts preserve P2P provenance and mark unresolved implementation details as `NEEDS CLARIFICATION`.
- `p2p spec export-status` lists the `speckit` target.
- `p2p spec export-show CHANGE-XXX --target speckit` prints the Spec Kit export index.
- Tests cover successful Spec Kit export and inspection.

## Tests / Verification

- T001: Support speckit export target (completed)
- T002: Generate Spec Kit feature directory (completed)
- T003: Preserve P2P governance boundary (completed)
- T004: Update P2P skill and tests (completed)
