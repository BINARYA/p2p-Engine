# Design - Portable Vertical Resolution Convergence 0.4.5

## Requirements Covered

- Reference resolution: R001-R007.
- Active project convergence: R008-R013.
- Governed lifecycle: R014-R018.
- Portable validation and machine behavior: R019-R022.
- Quality and compatibility: N001-N005, AC001-AC010.

## Key Decisions

- D001: Treat `VerticalCoordinate` as the canonical schema-v2 identity and
  never pass it through legacy ID normalization.
  Rationale: publisher, ID and version are already validated and persisted;
  normalizing the ID changes a valid public identity.

- D002: Replace the current lossy reference dictionary with a resolution
  inventory that preserves distinct coordinates and detects multiplicity.
  Rationale: one dictionary entry per bare ID cannot represent side-by-side
  versions or conflicting copies safely.

- D003: Keep legacy source precedence for non-portable bare IDs, but make
  portable ambiguity explicit.
  Rationale: this preserves existing v1 behavior while satisfying the exact
  resolution contract for v2 packs.

- D004: Make one lock-aware active-pack path authoritative for ordinary runtime
  reads.
  Rationale: active state already contains an additive coordinate and the lock
  already contains exact identity and checksum. Consumers must not reconstruct
  weaker identity from the bare ID.

- D005: Validate candidate identity completely before `AtomicMutationWriter`
  applies selection/adoption/migration files.
  Rationale: a successful governed mutation must not create state that the same
  engine immediately rejects. Pre-commit validation preserves atomic rollback
  semantics without introducing a compensating post-commit write.

- D006: Keep lifecycle JSON envelopes and storage schemas stable in `0.4.5`.
  Rationale: the release fixes conformance and should not force WaveKit to adopt
  another machine contract.

- D007: Route schema-v2 directories and archives through the portable package
  validator while retaining the legacy validator for v1 targets.
  Rationale: authoring and packaging must apply identical exact inheritance and
  safety semantics.

- D008: Preserve the MCP catalog and permissions; test corrected shared read
  behavior only.
  Rationale: public portable mutations were explicitly deferred by `PROP-103`,
  while existing MCP reads already delegate to the affected service.

## Components

- `src/p2p_engine/services/project_verticals.py`: reference inventory,
  exact/bare resolution policy, active-pack convergence, definition identity,
  readiness/coverage consumers and candidate validation.
- `src/p2p_engine/services/vertical_lifecycle.py`: lifecycle preconditions and
  apply result behavior only if needed to guarantee candidate validation.
- `src/p2p_engine/services/vertical_packages.py`: portable directory/archive
  validation and exact inheritance composition.
- `src/p2p_engine/cli_commands/project_ops.py`: schema-v2 target routing and
  stable public error/exit behavior.
- `src/p2p_engine/storage/filesystem.py`: compatibility facade only; no new
  domain rules.
- `tests/test_project_verticals.py`: legacy precedence, exact resolver,
  active/lock/definition drift and read-consumer tests.
- `tests/test_portable_verticals.py`: WaveKit-facing hyphenated lifecycle,
  side-by-side version and derived-pack integration tests.
- `tests/test_mcp.py`: existing read-surface regression only.
- `scripts/verify-release-artifacts.py` and installed-wheel smoke coverage:
  release artifact and isolated runtime proof.
- `CHANGELOG.md`, `docs/CLI-GUIDE.md`, `docs/INSTALL.md` and version metadata:
  corrected behavior and `0.4.5` release instructions.

## Reference Resolution Model

Discovery keeps the current low-to-high source precedence:

```text
bundled
-> user install
-> P2P_HOME install
-> project-local install
```

The resolver must retain enough information to build two logical indexes:

```text
coordinate -> all discovered copies of that exact coordinate
bare ID    -> all distinct legacy identities and portable coordinates
```

Resolution follows this order:

1. If the input contains coordinate syntax, parse it with
   `VerticalCoordinate.parse` and look up only its canonical string.
2. For an exact coordinate, compare all discovered semantic checksums.
3. If checksums differ, fail with `P2P_VERTICAL_COORDINATE_CONFLICT`.
4. If checksums agree, use the highest-precedence equivalent source.
5. For a bare input, try its trimmed lowercase spelling exactly.
6. If no exact bare spelling exists, apply the current legacy normalization and
   retry only for compatibility.
7. If the resulting bare family contains multiple portable coordinates or a
   portable/legacy identity collision, fail with
   `P2P_VERTICAL_AMBIGUOUS_REFERENCE` and require a coordinate.
8. If the family contains only legacy packs, retain current source precedence.

No semantic-version ordering is used to choose an active pack.

## Authoritative Active Identity

Ordinary filesystem reads use this state machine:

```text
missing active state
  -> read-only base_project fallback

active state + lock
  -> parse lock
  -> resolve lock.coordinate exactly when present
  -> validate lock checksum
  -> cross-check active ID/coordinate and lock ID/version
  -> authoritative pack

active state without lock
  -> active_vertical_coordinate when present
  -> otherwise legacy bare active_vertical_id
  -> existing missing-lock diagnostic remains visible
```

The active helper returns both `ActiveProjectVertical` and the resolved pack.
Callers that need the current pack reuse that pair instead of resolving
`active.vertical_id` again.

The following paths must converge on it:

- sections and section show;
- project context;
- definition show and definition patch context;
- progress and visible export callbacks;
- vertical read state and project memory;
- validation findings;
- proposal vertical coverage when coverage targets the active vertical;
- readiness when reading ordinary filesystem state.

Readiness candidate overlays keep their existing `ProjectReadinessSourceAccess`
boundary. They parse `active_vertical_coordinate` and candidate lock bytes from
the overlay, resolve that exact coordinate from installed packs, and perform
the same identity checks without falling back to ordinary filesystem bytes.

## Definition And Candidate Coherence

Definition validation extends the existing section/field checks with:

```text
definition.vertical_id      == pack.vertical_id
definition.vertical_version == pack.version
definition.lock.checksum    == resolved semantic checksum
```

Where an active lock is available, its checksum must equal the definition lock
checksum. Legacy missing-definition reads retain their current behavior; this
feature does not synthesize state during reads.

`validate_migration_candidate` validates the complete governed set before any
write:

```text
active.active_vertical_id         == target pack ID
active.active_vertical_coordinate == target coordinate for schema v2
lock.vertical_id                  == target pack ID
lock.coordinate                   == target coordinate for schema v2
lock.version                      == target version
lock.checksum                     == target semantic checksum
definition.vertical_id            == target pack ID
definition.vertical_version       == target version
definition.lock.checksum          == target semantic checksum
rubrics/questions                 == structurally valid candidate payloads
```

Selection, direct portable init, adoption and migration already use this
candidate renderer. Strengthening it protects all four workflows without a
second writer or a post-commit repair.

## Portable Validation Routing

`project vertical validate TARGET` classifies targets without writing:

- `.p2pv` ZIP: portable validator;
- canonical directory whose manifest declares schema version 2: portable
  validator;
- v1 path, directory or known bare ID: legacy validator.

Portable directory validation performs the same declared/effective inspection
as archive validation. Exact `extends` is resolved through the coordinate index
and its dependency checksum remains enforced by the package/lifecycle services.

JSON keeps the top-level `validation` field. Existing v1 payloads remain
unchanged; schema-v2 directories expose the same portable validation fields as
archives because that was the intended `PROP-103` contract.

## Public Surface And MCP Parity

- CLI contract: existing commands and options remain unchanged. The only
  intentional behavior change is explicit failure for references that were
  previously normalized incorrectly or selected ambiguously.
- MCP contract: no catalog, permission or mutation changes. Existing
  `p2p_project_vertical_*`, project context, sections and definition read tools
  inherit corrected service behavior.
- Storage contract: schema versions remain unchanged. No migration command is
  introduced.
- Documentation contract: exact coordinates are required for portable
  lifecycle automation and ambiguous bare references are documented.
- Test contract: service tests prove resolution and persistence; CLI tests
  protect machine behavior; MCP tests protect existing reads; isolated wheel
  tests prove packaged behavior.

## Error Handling

- `P2P_VERTICAL_AMBIGUOUS_REFERENCE`: a bare reference has more than one exact
  portable identity or collides with a legacy identity.
- `P2P_VERTICAL_COORDINATE_CONFLICT`: one coordinate resolves to different
  semantic checksums.
- Existing lock/definition diagnostics remain the primary workspace-validation
  codes for persisted state drift.
- Lifecycle command errors continue through the existing stable JSON envelope
  and non-zero exit behavior.
- Resolution and validation failures perform no writes.

## Migration And Compatibility

No persisted-state migration is required. Schema-v2 projects created by
`0.4.4` already contain the coordinate and lock data required by the corrected
resolver. After upgrading the runtime, valid affected projects should become
readable without mutating `.p2p` state.

Legacy state keeps these rules:

- missing active state remains a read-only `base_project` fallback;
- missing lock remains diagnosable and explicitly repairable;
- non-portable bare IDs retain source precedence;
- existing checksums and bundled pack semantics must not change.

## Risks And Tradeoffs

- Bare portable IDs that previously resolved through dictionary overwrite may
  now fail as ambiguous. This is intentional fail-closed behavior required by
  exact versioning.
- Centralizing active resolution touches several consumers. Regression tests
  must cover read-only behavior and candidate overlays to avoid hidden fallback
  changes.
- Comparing duplicate coordinate checksums adds discovery work, but pack roots
  are bounded and correctness is more important than silent conflict masking.
- Tightening definition version/checksum validation may expose previously
  hidden invalid state. Diagnostics must distinguish repairable legacy state
  from actual identity drift.

## Out Of Scope

- Downloading dependencies or artifacts.
- Selecting the newest semantic version.
- Editing or publishing catalog metadata.
- Clone-count lineage accounting.
- New MCP mutation parity.
- Universal restructuring of CLI JSON envelopes.
