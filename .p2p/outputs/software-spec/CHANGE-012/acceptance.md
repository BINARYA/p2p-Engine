# Acceptance

## Criteria

- `p2p spec refresh --change CHANGE-XXX` generates required artifacts under `.p2p/outputs/software-spec/CHANGE-XXX/`.
- `p2p spec status` lists generated specs.
- `p2p spec show CHANGE-XXX` prints `index.md`.
- `p2p spec prompt --change CHANGE-XXX` writes a refinement prompt.
- `p2p spec import CHANGE-XXX output-dir/` validates required files and YAML keys.
- Tests cover deterministic generation, prompt creation, status/show, and import.

## Tests / Verification

- T001: Generate deterministic software spec (completed)
- T002: Inspect generated software specs (completed)
- T003: Generate refinement prompt (completed)
- T004: Import refined software spec (completed)
- T005: Update skill and tests (completed)
