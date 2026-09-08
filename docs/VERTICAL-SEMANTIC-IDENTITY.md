# Vertical Semantic Identity V1

P2P Engine names the semantic checksum recipe frozen from release `0.6.7` as
`p2p-vertical-semantic-checksum/v1`. A complete identity is:

```json
{
  "contract": "p2p-vertical-semantic-checksum/v1",
  "algorithm": "sha256",
  "digest": "<64 lowercase hexadecimal characters>"
}
```

The contract version is independent from the P2P Engine version, vertical
semantic version, schema 3, portable-package format 1 and registry protocol
v2. A future checksum recipe must receive a new contract identifier; it must
not silently change v1 and does not by itself force a new vertical release.

## What V1 Identifies

V1 hashes the validated effective vertical after inheritance composition. Its
projection includes manifest metadata, dependencies, compatibility and domain
metadata together with sections, fields, completion policies, questions,
rubrics, artifacts, profiles, modules and the normalized **paths** of examples.
It excludes example file contents, host paths, registry/cache state, archive
metadata and the P2P runtime version.

Ordinary `examples/` files are documentary/reference resources. Changing only
their content at the same path leaves semantic v1 unchanged but changes the
artifact SHA-256. Renaming an example changes both because its path belongs to
the frozen v1 resource inventory. This historical asymmetry is compatibility
behaviour; neither side may be changed without a new checksum contract.

The projection is serialized exactly as the 0.6.7 implementation did: PyYAML
safe dump, sorted mapping keys, significant list ordering, escaped Unicode,
LF line endings, terminal newline and UTF-8 encoding, followed by SHA-256.
Static golden vectors under
`tests/fixtures/vertical_semantic_checksum/v1/` freeze the projection, exact
bytes and digest obtained from the official 0.6.7 wheel.

This identity is not the SHA-256 of `.p2pv` bytes. `artifact_checksum` detects
an exact archive-byte change; `semantic_identity` detects a change to the
interpreted effective vertical. Project-structure, bundle and blob checksums
are separate contracts as well.

During artifact inspection both values are **calculated** from supplied
content. Calculation alone is not verification against an external expected
value and says nothing about publisher authenticity or lineage. The separate
[portable provenance contract](VERTICAL-PROVENANCE-AND-LINEAGE.md) exposes this
status explicitly.

## Compatibility

Known legacy schema-3, lock, draft, transition, cache and registry-v2 fields
that contain only `semantic_checksum` are interpreted as v1/SHA-256 in memory.
Reads do not rewrite those documents. This fallback is limited to those known
fields and is never applied to an arbitrary 64-character checksum.

New public results and durable records include `semantic_identity` and retain
the scalar `semantic_checksum` as an alias derived from it. If both are
received they must agree exactly. Malformed values, v1 with an algorithm other
than SHA-256, unknown contracts at an integrity boundary, and contradictory
dual representations fail closed.

Registry v2 remains backward compatible: its existing scalar remains required
and valid by itself; structured `semantic_identity` and capability
`semantic_checksum_contracts` are optional additive fields and never belong in
`required_fields` for v2.

## Comparison And Future V2

Semantic comparison has three outcomes:

- same contract and digest: `equal`;
- same contract and different digest: `different`;
- different contracts: `incomparable`.

An incomparable result blocks any operation that requires proof of equality,
but does not claim that the content is different. A future v2 must add a new
calculator and static vectors while retaining v1 verification for immutable
releases already published. Existing releases and cache entries are never
rewritten merely to adopt the new contract.

Release version is itself part of the v1 projection. Correcting only example
prose in an unpublished working pack leaves v1 unchanged, but publishing that
correction after the prior coordinate exists requires a new coordinate
(normally a patch version), and that version change produces a new v1 digest.
Semantic equality never authorizes replacing different `.p2pv` bytes at one
immutable coordinate.

If examples later become executable or normative, they must be modeled as a
separate resource class with explicit consumers and safety rules. Ordinary
documentary examples must not silently acquire authority. Including a new
normative resource in semantic identity requires a separately specified
contract such as a future v2.

The `.p2pv` file does not embed its own semantic digest, avoiding a
self-reference. Offline inspection computes the identity from its existing
schema-3 content. Existing schema-3 dependency `checksum: sha256:<digest>`
fields are the narrowly recognized legacy v1 representation; optional
structured metadata may explain the same value but cannot contradict it.
