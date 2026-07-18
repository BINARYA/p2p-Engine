# Design - Runtime Surface And Derived-State Contract Closure

## Requirements Covered

- S1: R-S1-001..008.
- S2: R-S2-001..014.
- S3: R-S3-001..025.
- S4: R-S4-001..012.
- Cross-cutting: N001..014, E001..017 and AC001..018.

## Design Goals

- Close two explicitly unfinished feature tasks and two observed correctness
  defects without expanding product scope.
- Preserve external compatibility while making internal contracts explicit.
- Prefer semantic identity over file age or representation.
- Keep every read path side-effect free.
- Produce small independently reviewable slices with direct evidence.

## Key Decisions

- D001: Deliver four independent implementation slices under one closure
  feature.
  Rationale: they share release and compatibility gates, but forcing a common
  abstraction would couple unrelated domains.

- D002: Treat S1 as a public terminology correction only.
  Rationale: software-spec export behavior is valid and supported; the defect is
  its occasional misclassification as project definition.

- D003: Convert packaged seeds rather than maintaining mirrored single-file and
  multi-file copies.
  Rationale: mirrored semantic content creates two sources of truth and future
  drift.

- D004: Capture normalized seed payloads and checksums before changing resource
  layout, then use those snapshots as conversion gates.
  Rationale: source review alone is insufficient to prove lock compatibility.

- D005: Keep normalized semantic checksum as vertical identity and treat the
  resolved source path as diagnostic metadata.
  Rationale: an internal file split must not invalidate an otherwise identical
  project lock.

- D006: Build software-spec output through one pure candidate renderer used by
  refresh and freshness.
  Rationale: separate render implementations would drift and make semantic
  freshness untrustworthy.

- D007: Fingerprint renderer inputs, not every proposal or project file.
  Rationale: unrelated project work must not stale a spec.

- D008: Keep completeness and freshness as separate fields on
  `SoftwareSpecStatus`.
  Rationale: changing the meaning of existing `status=generated` would break
  callers; additive freshness communicates the new contract.

- D009: Mark newly generated and newly imported artifacts explicitly, while
  classifying legacy artifacts conservatively.
  Rationale: provenance cannot be reconstructed reliably from mtime or directory
  naming.

- D010: Remove mtime comparison only for the aggregate `software_specs` node.
  Rationale: other freshness nodes have separate ownership and fallback
  contracts that this feature does not redesign.

- D011: Let Change Set registry lifecycle determine generated-action
  eligibility and use decision context only for explanation.
  Rationale: an incomplete derived index must not suppress operational work.

- D012: Generate stable Change Set action IDs from the target Change Set ID.
  Rationale: positional IDs change when an earlier action is added and make
  clients see false identity churn.

- D013: Build all eligible Change Set actions before applying caller limits.
  Rationale: `--top`/`top` already provide an explicit bounded read contract.

- D014: Reuse existing CLI and MCP tools; add no new write surface.
  Rationale: all externally visible changes are terminology or read-only derived
  behavior.

## Slice S1 - Software-Spec Terminology

### Components

- `src/p2p_engine/cli_commands/specs.py`
  - Correct the `spec export` docstring and audit sibling command wording.
- `src/p2p_engine/mcp/catalog/work_specs.py`
  - Confirm native-spec versus target-export descriptions are unambiguous.
- `docs/CLI-GUIDE.md`, `docs/MCP.md`, `docs/GLOSSARY.md`
  - State the compatibility boundary and point project publication/export to
    `p2p project export`.
- Source templates and generated agent skills
  - Update only through the existing template/generation ownership path.
- `tests/test_cli.py`, `tests/test_mcp_registry.py`,
  `tests/test_docs_root_mcp_hygiene.py`
  - Add public terminology assertions at the narrowest useful layer.

### Contract

The command family remains:

```text
p2p spec refresh/status/show/prompt/import
p2p spec export/export-status/export-show/export-validate
```

The first group owns P2P-native software specs. The second group owns
target-specific software-spec handoff bundles. Neither is the default
human-visible project definition export.

Tests should assert required positive phrases rather than globally banning the
words "project definition", because documentation may legitimately contrast
this workflow with `p2p project export`.

## Slice S2 - Canonical Bundled Seed Packs

### Canonical Resource Shape

Each bundled pack becomes:

```text
src/p2p_engine/resources/verticals/<vertical-id>/
  manifest.yml
  vertical.yml
  rubrics.yml
  sections/
    <priority>-<stable-section-id>.yml
```

`manifest.yml` owns package identity and schema metadata. `vertical.yml` owns
vertical metadata and references/inline values that do not have a canonical
split file. Each section file owns exactly one section; its zero-padded priority
prefix preserves deterministic public ordering. `rubrics.yml` owns all rubrics.
Optional directories are created only for actual content.

### Conversion Procedure

1. Load each current single-file seed through the production loader.
2. Serialize a test-only canonical normalized snapshot and checksum.
3. Split content mechanically into canonical files.
4. Load the new pack through the production canonical loader.
5. Compare typed normalized payload, checksum, section/rubric ordering and
   externally visible list/show/context results.
6. Delete aggregate section/rubric bodies from `vertical.yml`.

The snapshot is test evidence, not a second production resource.

### Lock And Source Compatibility

`_pack_checksum(pack)` remains based on the normalized semantic payload.
`VerticalPackSource.resolved_from` for an internal seed remains:

```text
p2p_engine.resources.verticals/<vertical-id>
```

The resolved diagnostic `path` changes to `manifest.yml`. Existing lock status
must ignore that representation-only difference and continue to compare the
semantic checksum. No automatic lock rewrite is introduced.

### Packaging

`scripts/verify-release-artifacts.py` should define the four bundled pack IDs
once and derive required canonical members for wheel and sdist. A verification
test must fail when any manifest, vertical metadata, rubrics file or section
file is missing. A built-artifact smoke test should import resources from an
isolated installation or archive extraction, not from `src/`.

### Main Tests

- `tests/test_project_verticals.py`
  - canonical loading, normalization, checksum and old-lock validity;
  - external single-file compatibility and resolver precedence;
  - unchanged `base_project` fallback and software vertical sections.
- Release verifier tests or focused script tests
  - complete wheel/sdist resources and forbidden-root rules.

## Slice S3 - Semantic Software-Spec Freshness

### Core Models

Extend `SoftwareSpecStatus` additively:

```text
status: generated | incomplete
freshness: current | current_legacy | stale | modified | unknown_origin | incomplete
origin: generated | imported | legacy_generated | legacy_unknown
current_source_fingerprint_sha256: string
recorded_source_fingerprint_sha256: string
changed_sources: tuple[string, ...]
changed_outputs: tuple[string, ...]
reasons: tuple[string, ...]
```

Exact field names may follow established serialization conventions, but the
completeness/freshness separation is mandatory.

A private or core immutable `SoftwareSpecCandidate` should contain:

- `change_id` and title;
- ordered required-file content;
- ordered source descriptor records;
- source fingerprint;
- generator contract version.

### Pure Candidate Builder

Refactor `SoftwareSpecService.refresh()` into:

```text
capture authoritative render inputs
-> render_candidate(inputs)
-> atomically write owned required files
-> return status
```

`statuses()` uses the same capture and render path but never calls the writer.
The source collector must list every source whose values are read by rendering.
If `show_proposal()` reads a composite view, either fingerprint its canonical
semantic input or narrow rendering to explicitly captured source documents.
The fingerprint cannot list only `proposal.md` while rendering values derived
from other artifacts.

### Fingerprint Contract

The semantic payload is versioned and canonical:

```yaml
software_spec_source:
  contract_version: 1
  renderer_version: 1
  change_id: CHANGE-001
  sources:
    - path: .p2p/changes/CHANGE-001/change.md
      sha256: ...
    - path: .p2p/changes/CHANGE-001/tasks.yml
      sha256: ...
    - path: .p2p/proposals/PROP-001/proposal.md
      sha256: ...
```

Source records are ordered by normalized relative path. YAML semantic sources
may be hashed as canonical payloads only when that normalization policy is
explicit and versioned. The aggregate fingerprint hashes the canonical source
descriptor plus renderer and contract versions.

Generated provenance gains a reserved additive block, for example:

```yaml
p2p_generation:
  schema_version: 1
  origin: generated
  generator: p2p_engine.software_spec
  renderer_version: 1
  source_fingerprint:
    algorithm: sha256
    value: ...
  sources:
    - path: ...
      sha256: ...
  outputs:
    - path: index.md
      sha256: ...
```

Import parses caller provenance and writes `origin: imported` in the reserved
block without deleting caller keys. The implementation must define whether an
existing reserved block is rejected or replaced; the recommended behavior is
to reject conflicting engine-owned metadata with an actionable error.

The output digest list excludes `provenance.yml` to avoid a self-referential
hash. For generated specs, status also renders the complete current candidate:
matching source fingerprint plus differing candidate bytes reports `modified`,
while a differing source fingerprint reports `stale`.

### Legacy Classification

Legacy fallback must be conservative:

1. Missing required file -> `incomplete`.
2. Valid current reserved block with `origin=generated` -> fingerprint compare.
3. Valid current reserved block with `origin=imported` -> `unknown_origin`
   unless a supported external source contract is present.
4. No reserved block:
   - render the current non-provenance candidate without writes;
   - validate the old `source` and `generated_from` structure;
   - exact non-provenance equality plus coherent legacy provenance ->
     `current_legacy`;
   - coherent recognizable generated provenance plus changed candidate ->
     `stale`;
   - otherwise -> `unknown_origin`.

The legacy comparison excludes `provenance.yml` because the new renderer adds
metadata that old output cannot contain. It compares every other required file
byte-for-byte.

If authoritative sources are missing, status is `unknown_origin` or
`incomplete` with a reason; a read must not create replacement source or output.

### Aggregate Mapping

`DerivedFreshnessService` maps per-spec results:

| Per-spec set | Aggregate node |
| --- | --- |
| all `current` | `current` |
| `current` and at least one `current_legacy` | `current_legacy_fallback` |
| any `stale` or `modified` | `stale` |
| any `unknown_origin` or `incomplete`, no stale | `partial` |
| no specs | existing optional empty-set state |

No dependency/output mtime comparison occurs in this branch. Existing upstream
dependency propagation remains, but an unrelated canonical change must not
enter the spec fingerprint or force aggregate stale by age.

### Failure And Concurrency Behavior

- Candidate capture uses one coherent source snapshot per spec status
  evaluation.
- If a source changes during capture, return a stable
  `source_changed_during_read` diagnostic or retry once under an explicit
  bounded policy.
- Malformed provenance produces `unknown_origin`, not a crash of the whole
  project freshness graph.
- One unreadable spec produces a per-spec diagnostic and aggregate `partial`.
- Refresh and import commit all required files through one atomic mutation. A
  failure-injection test must prove the old complete set remains intact.
- Status and freshness tests compare workspace tree hashes before and after.

### Main Tests

- `tests/test_software_spec_service.py`
  - pure candidate, provenance, imports, legacy classification and idempotence.
- `tests/test_derived_freshness_service.py`
  - aggregate mapping, unrelated changes and downstream propagation.
- `tests/test_cli.py` and relevant MCP handler tests
  - additive fields and stable reason codes.

## Slice S4 - Complete Active Change Actions

### Eligibility

The Change Set registry is the lifecycle authority. Records with a nonblank ID
and a status outside:

```text
completed, cancelled, superseded
```

produce a generated action. Malformed blank IDs are skipped with existing
registry diagnostics rather than creating an invalid action.

Decision context enriches `reason` with included proposal IDs when available.
No `change_id in change_nodes` eligibility test remains.

### Identity And Ordering

Use a collision-resistant stable ID derived from kind and target, for example:

```text
NEXT-CHANGE-CHANGE-069
```

The final format must be documented and covered as a public generated-identity
contract. Curated IDs remain unchanged.

Sort eligible Change Sets before rendering:

1. explicit high-action statuses such as `blocked` and `planned`;
2. other non-terminal statuses;
3. stable Change Set ID.

If domain lifecycle ordering already defines a more accurate status rank, reuse
that single source rather than duplicate it. Unknown non-terminal statuses stay
visible at medium priority and sort after known active statuses.

The complete actions enter the existing composition and dedupe pipeline.
`list(limit=N)` slices only after dedupe. A curated `(continue_change,
CHANGE-XXX)` action appears earlier and suppresses its generated equivalent.

### Public Parity

- CLI `p2p next --top N` and MCP `p2p_next(top=N)` serialize the same prefix.
- Omitting a limit returns the complete action set.
- `p2p next refresh`/`p2p_next_refresh` reports the complete deduped generated
  count but still persists only normalized curated actions.
- No generated action is added to `next-actions.yml`.

### Main Tests

- `tests/test_next_actions_service.py`
  - zero, one, two and many active changes;
  - mixed terminal/active/unknown statuses;
  - missing decision-context node;
  - stable identity/order and curated dedupe;
  - limits and generated count.
- `tests/test_cli.py`, `tests/test_mcp.py`
  - CLI/MCP bounded parity and multi-change visibility.

## Public Surface And MCP Parity

- CLI contract: existing commands remain; wording and additive read fields
  change as specified.
- MCP contract: existing catalog/handlers remain; descriptions and serialized
  read results track CLI/service behavior.
- Storage contract: packaged vertical resources change layout; generated
  software-spec provenance gains an additive versioned block.
- Documentation contract: explain compatibility export, canonical resource
  format, semantic freshness and complete generated actions.
- Test contract: service, CLI, MCP, release artifact, installed-package smoke,
  public suite and full suite.

## Migration And Compatibility

No workspace schema migration is required.

- Single-file external packs remain valid compatibility input.
- Existing packaged-seed locks remain valid through semantic checksum
  equivalence.
- Existing software specs are classified lazily and read-only. They are not
  rewritten until the owner explicitly runs an existing refresh/import command.
- Newly refreshed/imported specs receive the additive provenance block.
- Existing clients that read `SoftwareSpecStatus.status` continue to see
  completeness. New clients may consume freshness detail.
- Generated next actions are derived and noncanonical; their stable ID format
  may change once as part of this correction and is documented.

## Delivery Order

```text
P -> S1 -> S2 -> S3 -> S4 -> I -> F
```

S1 and S2 close the two existing unfinished tasks. S3 and S4 correct observed
runtime behavior. Slices may be implemented in separate commits. The
integration gate follows all four because packaged-resource and public-contract
tests span multiple slices.

## Risks And Tradeoffs

- A seed split can reorder lists without changing IDs; golden typed-model
  equality must include order where public output preserves it.
- Existing locks may carry an old diagnostic path even while valid. Rewriting
  them would create unnecessary workspace churn.
- Legacy provenance cannot perfectly distinguish generated from imported
  content. Conservative `unknown_origin` is preferable to false certainty.
- Pure rendering can expose hidden source reads in current proposal views. The
  source collector must be corrected rather than broadening the fingerprint to
  the whole workspace.
- Stable generated next-action IDs are a public behavior adjustment. The new
  format must not collide with curated IDs or depend on ordering.
- Testing only from `src/` can miss incomplete wheels. Built-artifact checks are
  mandatory for S2.

## Out Of Scope

The out-of-scope boundaries in `requirements.md` are normative. In particular,
this design does not authorize workspace artifact refresh, package release,
Git publication or manual `.p2p` edits.
