# WaveKit Vertical Transition Handoff

## Purpose

P2P Engine 0.6.4 retains the vertical lifecycle `impact` object introduced in
0.4.8 and binds it to the current receipt and release contracts through the
versioned `p2p-vertical-transition-impact/v1` contract. This note defines
the evidence WaveKit can use to close task `7.8` without interpreting P2P
workspace files or reproducing transition rules outside P2P Engine.

The supported integration boundary remains the P2P CLI JSON contract. WaveKit
must treat `.p2p/` as worker-owned state and must not inspect it to infer whether
adoption or migration is safe.

## Release Fixture Manifest

The sanitized handoff fixtures and their checksums are declared in:

```text
tests/fixtures/vertical_transition/manifest-v1.json
```

The manifest binds:

- P2P Engine `0.6.4`;
- global CLI contract `p2p-cli/v1`;
- impact contract `p2p-vertical-transition-impact/v1`;
- plan contract `p2p-vertical-transition-plan/v1`;
- mutation receipt schema `3`;
- exact per-collection and total-impact limits;
- the SHA-256 checksum of every handoff fixture.

Regenerate the current members and manifest deterministically with
`scripts/generate-wavekit-transition-fixtures.py`; use `--check` in validation.
`legacy-0.4.7-characterization.json` is historical input only and is never
indexed as a current 0.6.4 output.

The fixtures cover populated adoption, migration requiring owner decisions, a
complete canonical plan and the resulting apply response. They contain domain
identities, counts, dispositions and hashes, but no workspace paths, raw field
values, question answers, credentials or physical postcondition hashes.

## WaveKit 7.8 Assertions

WaveKit can close the remaining transition assertions by proving both of the
following against the release-candidate wheel:

1. Empty projects may adopt a selected vertical, while any meaningful
   definition, assumption, blocker, existing orphan, owner-question evidence
   or rubric customization routes to a blocked migration-required result.
2. A populated migration cannot become applicable until every required
   decision is represented by a current canonical plan; after re-preview and
   apply, the typed semantic postconditions and replay result are stable.

WaveKit should deserialize only the documented contract fields. It must fail
closed on unknown contract versions, unknown dispositions, truncated impact,
missing fingerprints or a blocked preview without a stable issue code.

## Expected Orchestration

The server-side sequence is:

```text
migrate preview without plan
-> persist/display required decisions
-> build canonical plan
-> migrate preview with plan
-> replace the prior preview token
-> migrate apply with current token and idempotency key
-> inspect receipt status or exact replay when recovery is required
```

The first preview is successful but blocked and intentionally has no applicable
preview token. A complete plan is bound to the analysis fingerprint. Any
meaningful source, target, plan, actor or candidate change requires a new
preview.

Install is a separate non-activating operation. Its result reports
`installed_coordinate`, `installed_semantic_checksum` and
`installed_artifact_checksum`. Only adoption and migration report
`active_coordinate` and the active project artifact postconditions.

## Responsibility Boundary

P2P Engine owns evidence classification, structural analysis, required
decisions, plan validation, candidate materialization, workspace validation,
atomic mutation and receipt semantics.

WaveKit continues to own:

- authentication and project authorization;
- operation expiry and user-facing confirmation policy;
- per-project queue serialization and cross-project concurrency;
- worker crash supervision and retry scheduling;
- persistence of operation/audit records in PostgreSQL;
- post-apply product-level validation and notifications;
- Angular, MCP HTTP and mediator presentation of the typed result.

WaveKit must not add a second mapping format or a custom workspace-to-server
adapter. All project-state reads and writes remain mediated by registered P2P
CLI operations.
