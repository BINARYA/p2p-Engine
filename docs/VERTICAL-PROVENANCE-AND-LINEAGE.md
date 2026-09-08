# Portable Vertical Provenance And Lineage V1

P2P Engine exposes the contract
`p2p-vertical-portable-provenance/v1` when it successfully inspects a portable
vertical. The contract explains what can be learned from the artifact itself;
it is not an audit record, trust score or third form of artifact identity.

## Evidence Vocabulary

- `calculated`: P2P deterministically derived the value from supplied content.
  This is not verification against an external expected value.
- `verified_against_reference`: P2P calculated a supplied target's complete
  identity and successfully compared it with a separately declared identity.
- `verifiable_when_available`: the declaration contains an identity that can
  be checked once target content is explicitly supplied.
- `declarative_unverified`: the artifact makes a syntactically valid claim but
  supplies no integrity or authenticity proof for the relationship.
- `unavailable`: the evidence does not exist at this boundary.

Archive SHA-256 and vertical semantic identity are `calculated`. P2P hashes the
bytes or effective content it has received; it does not thereby prove who
authored or published them. Archive safety and canonical-layout validation are
separate from identity calculation.

## Portable Declarations

A schema-3 `.p2pv` carries:

- its claimed publisher, vertical ID, release version and license;
- `manifest.source`, exposed as a construction-source declaration rather than
  a registry URL or trust source;
- optional `forked_from` and `previous_release` coordinates;
- structural `extends` and direct dependency coordinates with semantic
  identities;
- compatibility and domain metadata.

Publisher, license and construction source are declarations. They do not prove
publisher control, ownership, legal compliance or the environment in which the
artifact was built.

`forked_from` and `previous_release` are portable but declarative lineage. Even
if a parent with the named coordinate is locally available, its existence does
not prove that the child was derived from it. P2P does not infer lineage from
clone origin, `extends`, dependencies, matching publisher or matching content.

## Dependencies

A dependency contains two separate facts:

1. the child declares a dependency relationship and exact coordinate;
2. the child declares the expected semantic identity of the target.

The relationship always remains `declarative_unverified`. When target content
is explicitly available, P2P can calculate its semantic identity and compare
it with the declaration. Only the target identity becomes
`verified_against_reference`; the relationship does not become authenticated
or trusted.

Dependency artifact SHA-256 is not embedded in schema 3. A registry release or
transfer envelope may bind exact target bytes, but that is external context and
does not become part of the child artifact's portable provenance.

## Authoring And Host Context

Draft origin, draft `source_attribution`, package/publication evidence,
registry URL, authenticated uploader, moderation, review, timestamps, receipt,
cache path and WaveKit identifiers depend on the system handling the artifact.
They are not portable artifact facts.

`vertical draft create --from` remains a clone. It records origin and source
attribution in mutable draft state, while only an explicitly selected
`forked_from` or `previous_release` relationship enters the materialized pack.
Materialization intentionally excludes arbitrary `source_attribution`.

Project-structure export therefore does not claim
`legal_attribution_preserved: true`. Portable attribution is represented only
by the concrete publisher, license and explicit lineage fields written to the
pack.

## Inspection

These commands expose the same provenance object whenever actual artifact
content is inspected:

```bash
p2p vertical inspect ./release.p2pv --format json
p2p project vertical inspect ./release.p2pv --format json
```

An archive has a calculated artifact SHA-256. An unpackaged source directory
reports artifact identity as `unavailable`, while semantic identity is still
calculated after successful composition and validation. An inherited vertical
requires its structural dependency content to be explicitly available; inspect
does not fetch the network merely to improve provenance status.

An exact-byte transfer through a local project, registry, WaveKit instance or
peer preserves artifact SHA-256, semantic identity and portable declarations.
Each host may retain different external context without changing the `.p2pv`.

This is lossless only at the artifact and intrinsic portable-declaration
layers. It does not restore draft revisions/evidence, project state, registry
records, authenticated publication context or host audit. P2P therefore uses
the artifact directly for immutable workflows and requires an explicit clone/
derive transition for editing; see
[Vertical Artifact Lifecycles](VERTICAL-ARTIFACT-LIFECYCLES.md).

## Core Boundary And Future Evolution

Portable provenance core contains only declarations, deterministic identity
calculations and comparisons against explicitly supplied target content. It
does not model trust, audit, moderation, uploader identity, registry trust or
WaveKit-specific provenance.

Offline proof of ancestry would require a separate format decision with typed
parent semantic and artifact identities. Publisher authenticity would further
require signatures and a complete trust, revocation and key-rotation model.
Those concerns are deliberately outside provenance v1; schema 3, package
format 1, registry v2 and `p2p-vertical-semantic-checksum/v1` remain unchanged.
