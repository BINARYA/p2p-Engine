# Design

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- `p2p spec export --change CHANGE-XXX --target generic`
- `p2p spec export --change CHANGE-XXX --target openspec`
- `p2p spec export-status`
- `p2p spec export-show CHANGE-XXX --target TARGET`
- Generic export bundle under `.p2p/outputs/spec-export/CHANGE-XXX/generic/`
- OpenSpec-oriented export bundle under `.p2p/outputs/spec-export/CHANGE-XXX/openspec/`
- P2P skill guidance for exporting from the P2P-native software spec layer.
- Tests for successful export, export inspection, and unsupported target rejection.
