# Acceptance

## Criteria

- `p2p spec export-validate CHANGE-XXX --target generic` validates generic bundle structure.
- `p2p spec export-validate CHANGE-XXX --target openspec` validates OpenSpec-oriented bundle structure.
- `p2p spec export-validate CHANGE-XXX --target speckit` validates Spec Kit-oriented bundle structure.
- Missing required export artifacts fail explicitly.
- Manifest mismatch failures are reported explicitly.
- Validation is read-only and does not regenerate or mutate export bundles.

## Tests / Verification

- T001: Validate generic export bundles (completed)
- T002: Validate OpenSpec-oriented export bundles (completed)
- T003: Validate Spec Kit-oriented export bundles (completed)
- T004: Report invalid export bundles (completed)
- T005: Update P2P skill and tests (completed)
