# Implementation Note - PROP-106 Vertical Draft Lifecycle

## Status

Delivered for version `0.4.6` from accepted proposal `PROP-106`.

## Delivered

- Versioned normalized document, draft-state and evidence contracts with
  deterministic hashes, bounded input and user-level storage outside `.p2p`.
- Empty drafts with zero sections and readiness 0, plus exact effective-content
  cloning from the local catalog.
- Explicit, independent `extends`, `lineage.forked_from` and
  `lineage.previous_release` references with exact semantic checksums.
- Complete-document optimistic updates with per-draft locking, stale-write
  rejection and downstream evidence invalidation.
- One normalized-document compiler for canonical schema-2 directories, fresh
  target atomic commit and inspect/materialize/inspect round-trip checks.
- Revision/hash-bound validation and deterministic package evidence; package
  and publication never rematerialize implicitly.
- Immutable idempotent local add through the `PROP-105` cache writer, including
  mixed bundled/cached dependency closure resolution.
- Authenticated provider-neutral registry publication of the exact `.p2pv`
  artifact with caller idempotency key, typed provider failures and exact
  receipt verification.
- Stable zero-section installation failure and
  `P2P_VERTICAL_NO_TARGET_SECTION` proposal guard shared by CLI and MCP before
  proposal allocation.
- Eight `p2p vertical draft` CLI commands under `p2p-cli/v1`, plus five stable
  WaveKit-oriented payload fixtures.

## Integration Boundary

WaveKit edits and submits the complete normalized document. P2P Engine owns
canonical file materialization, validation, packaging, cache integrity and
registry protocol details.

```text
WaveKit worker -> p2p vertical draft ... -> user-level draft/evidence
              -> canonical pack -> exact .p2pv -> local cache or registry
```

Drafts do not enter project memory. A project sees a vertical only after the
immutable artifact follows the existing portable install and selection path.
The proposal guard is in `P2PWorkspace`, so existing CLI and MCP proposal
creation use the same active-section rule.

## Failure Policy

- No stale complete-document replacement.
- No placeholder section in an empty draft.
- No materialization into a non-empty target.
- No package from missing, failed or drifted validation evidence.
- No local add or publication from a changed package.
- No immutable-coordinate replacement with different content.
- No registry token in draft evidence, JSON payloads or persisted failures.
- No proposal allocation when the active vertical exposes zero target sections.

## Deferred

Direct draft-authoring MCP tools remain intentionally deferred. A complete
document update is a large persistent write that needs a separate MCP consent
and request-size policy. WaveKit 0.4.6 integration uses its serialized worker
and the CLI JSON contract. Existing MCP proposal creation is covered by the
shared no-target-section domain guard.

## Validation Evidence

- Dedicated draft suite: `11 passed`.
- Focused vertical/registry/portable/project/MCP/CLI regression:
  `169 passed`.
- Full repository suite: `1446 passed in 281.24s`.
- Wheel and sdist build succeeded for `0.4.6`.
- Release verifier passed with `wheel_files=256` and `sdist_files=519`, and now
  requires all draft/registry modules, documentation, tests and WaveKit golden
  fixtures.
- The wheel was installed with no source-package import path and successfully
  executed `vertical draft create --empty --format json`, returning
  `p2p-cli/v1` plus the three independent draft contract versions.
