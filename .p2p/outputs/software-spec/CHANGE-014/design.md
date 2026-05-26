# Design

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- `p2p spec export --change CHANGE-XXX --target speckit`
- Spec Kit-oriented export index and manifest.
- Feature directory under `.p2p/outputs/spec-export/CHANGE-XXX/speckit/specs/CHANGE-XXX-slug/`
- `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, and `contracts/README.md`
- P2P skill guidance for Spec Kit export usage and governance boundary.
- Tests covering successful Spec Kit export and export inspection.
