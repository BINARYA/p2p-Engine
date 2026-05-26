# Design

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- Managed Git policy levels from advisory to owner-controlled merge.
- `p2p work plan --change CHANGE-XXX --target TARGET`
- `p2p work list`
- `p2p work show WORK-XXX`
- `.p2p/work/WORK-XXX/manifest.yml` model.
- Work manifest fields for source Change Set, proposals, handoff target, export validation, logical branch name, allowed files, and disabled auto branch/commit/merge policy.
- P2P skill guidance for routing comments, choices, Change Sets, exports, and Work manifests.
- Tests for manifest creation and inspection.
