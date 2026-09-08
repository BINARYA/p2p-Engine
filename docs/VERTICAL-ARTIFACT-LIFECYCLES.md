# Vertical Artifact Lifecycles

P2P Engine has two vertical lifecycles. It does not have a third `exact import`
lifecycle.

An immutable `.p2pv` is the lossless representation of the portable artifact
layer only. A byte-identical copy preserves the artifact bytes and portable
declarations and allows P2P to recalculate artifact and semantic identity. It
does not reconstruct draft, host attribution, registry, audit or WaveKit state.

```text
immutable release: .p2pv -> inspect / verify / pull / cache / install / use
editable release:  .p2pv -> explicit clone/derive -> draft -> new release
```

## What Exact Preservation Means

`Lossless` must always name the layer being preserved:

| Layer | Preserved by copying one `.p2pv`? |
|---|---:|
| canonical archive bytes and artifact SHA-256 | yes |
| versioned semantic identity | yes, when calculated from the same effective content |
| coordinate and portable declarations | yes |
| explicit portable lineage and dependency references | yes |
| draft ID, revisions and evidence | no |
| arbitrary draft `source_attribution` | no |
| project state produced after installation | no |
| registry URL, uploader, review, moderation and receipt | no |
| WaveKit identifiers, timestamps and host audit | no |

The missing values were never part of the artifact. Their absence is a format
boundary, not data that an import command could recover.

## Inspect Or Use An Immutable Release

Inspecting an artifact is read-only:

```bash
p2p vertical inspect ./release.p2pv --format json
```

For direct offline project initialization, retain an independently obtained
artifact SHA-256 and pass both values explicitly:

```bash
p2p init "My Project" \
  --vertical-pack ./release.p2pv \
  --expected-checksum <artifact-sha256>
```

This consumes the release into project-owned structure. It does not create a
vertical draft or add the artifact to the user cache.

For a configured registry, `p2p vertical pull` verifies the release and its
dependency closure before atomically caching the immutable artifacts. Cache is
managed release storage, not authoring state.

## Clone Only When Editing

Use `vertical draft create --from` only to create an editable derivative:

```bash
p2p vertical draft create \
  --from publisher/vertical@1.0.0 \
  --version 1.0.1 \
  --previous-release publisher/vertical@1.0.0
```

The result is a fresh mutable draft with its own draft ID, revision and
evidence. P2P may normalize effective content and authoring metadata. Clone
origin remains local context; portable `forked_from` and `previous_release`
lineage are included only when explicitly selected.

`draft create --from` is not deserialization, restore or a promise that a later
package will be byte-identical to the source artifact. Editing always proceeds
through a draft and a subsequent immutable release.

## Recovery Belongs To The Owning Layer

| State to recover | Required recovery source |
|---|---|
| artifact bytes | preserved `.p2pv` or artifact-store backup |
| user cache | registry pull or the host's existing cache backup procedure |
| project memory | P2P project bundle or physical project backup |
| vertical draft | backup of the user draft store |
| registry or WaveKit state | the host database, audit and artifact backups |

Possessing an artifact permits inspection of its intrinsic content. It does
not prove publication authority or recreate external trust and audit context.

Future offline or replica scenarios might expose another cache-related need.
No concrete requirement currently exists, and no API or lifecycle is defined.
It should be reconsidered only from a demonstrated use case and the future P2P
replica model.
