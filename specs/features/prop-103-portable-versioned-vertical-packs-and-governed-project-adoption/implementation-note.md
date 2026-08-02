# Implementation Note - PROP-103 Portable Versioned Vertical Packs

## Status

Implemented on 2026-08-02 from accepted proposal `PROP-103`.

## Delivered

- Portable schema version 2 with exact coordinate, semantic version, license,
  structural inheritance, social lineage and exact dependency checksums.
- Safe deterministic `.p2pv` ZIP artifacts with fixed metadata, canonical
  content and bounded pre-extraction validation.
- Recursive exact-coordinate resolution and side-by-side installed versions.
- Machine-facing schema, scaffold, inspect, validate and package commands.
- State-bound install, adopt and migrate preview/apply commands with stable JSON
  envelopes, explicit confirmation and actor attribution.
- Existing durable project transaction lock, source preconditions, rollback
  journal and atomic writer reused for every apply.
- `p2p init --vertical-pack --expected-checksum` preflight and exact selection.
- Same-ID evidence preservation, explicit exact field/rubric mapping and durable
  project-definition orphans for unmapped evidence.
- Additive exact coordinate, artifact checksum and dependency closure in the
  active lock while preserving version-1 lock parsing.
- CLI guide, concepts and primitive inventory updates.

## Integration Boundary

P2P Engine performs no network access. WaveKit remains responsible for catalog
queries, visibility, licensing policy, moderation, counters, artifact download
and authorization. WaveKit supplies a local immutable artifact and expected
checksum, then invokes the CLI.

Each install operation commits one target artifact atomically after its complete
dependency closure is already present locally and checksum-valid. Dependency
download and ordered delivery remain caller responsibilities.

## Deferred

Public MCP mutation tools are intentionally deferred from this delivery. The
package and lifecycle behavior is isolated in typed services so a future MCP
adapter can reuse the exact validation, preview and apply paths without
duplicating domain logic.

## Validation Evidence

- Portable and legacy vertical tests: `44 passed`.
- Public CLI/MCP suite: `264 passed`, `1193 deselected`.
- Focused service/adapter suite: `1452 passed`, `3 skipped`.
- Full suite after final test expansion: `1454 passed`, `3 skipped`.
- Release artifacts: wheel `244` files, sdist `496` files, both verified.
- Installed-wheel smoke: `p2p project vertical schema --format json` succeeded
  outside the source checkout.

The full-suite run exposed an existing convergence race classification: a
second process could correctly detect changed preconditions but report generic
`failed`. The service now maps that outcome to its documented `stale_preview`
status; the dedicated 16-test convergence suite and the full suite pass.
