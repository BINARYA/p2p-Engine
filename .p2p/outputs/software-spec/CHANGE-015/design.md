# Design

## Implementation Targets

local_cli

## Data Flow

Not specified yet.

## CLI/API Surface

Not specified yet.

## Storage / Artifacts

- `p2p spec export-validate CHANGE-XXX --target TARGET`
- Read-only validation for generic export bundles.
- Read-only validation for OpenSpec-oriented export bundles.
- Read-only validation for Spec Kit-oriented export bundles.
- Manifest coherence checks for `source.change` and `target`.
- Tests for valid bundles, missing files, and manifest mismatch failures.
- P2P skill guidance for validating export bundles before downstream use.
