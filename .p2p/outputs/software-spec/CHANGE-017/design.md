# Design

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- Read-only Git adapter functions for local `p2p/work/*` branch discovery.
- `p2p work scan`
- Aggregated `.p2p/registries/work.yml`
- `p2p work list` visibility for scanned branch Work items.
- Tests proving Work manifests can be read from a local P2P-managed branch without checkout.
- P2P skill guidance for branch scan boundaries.
