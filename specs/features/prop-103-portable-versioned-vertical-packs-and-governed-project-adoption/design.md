# Design - Portable Versioned Vertical Packs And Governed Project Adoption

## Decision Summary

Implement the accepted `PROP-103` as an additive local runtime contract. P2P
Engine never contacts a registry. WaveKit or another trusted caller downloads
an immutable artifact, verifies its policy context, and passes a local path plus
expected checksum to the CLI.

## Ownership Boundaries

- `core/project_verticals.py` owns additive typed fields for portable identity,
  dependency locks and preserved migration orphans.
- `services/vertical_packages.py` owns archive safety, schema output,
  scaffold/inspect/validate/package behavior and deterministic bytes.
- `services/vertical_lifecycle.py` owns install/adopt/migrate preview/apply,
  token validation and project-scoped locking.
- `services/project_verticals.py` remains the semantic pack loader, composer,
  validator and definition-state renderer. It gains exact-coordinate and
  recursive project-pack resolution without becoming a registry client.
- `storage/filesystem.py` exposes facade methods only; domain behavior remains
  in services.
- `cli_commands/project_ops.py` owns presentation, JSON envelopes, argument
  validation and exit codes.
- `cli.py` integrates explicit pack installation into project initialization.

## Portable Pack Layout

```text
manifest.yml
vertical.yml
sections/*.yml
rubrics.yml
profiles/*.yml       # optional
modules/*.yml        # optional
artifacts/*.yml      # optional
examples/*.{yml,yaml,json,md}  # optional
```

`manifest.yml` version 2 adds:

```yaml
schema_version: 2
publisher: example
id: software_project
version: 2.1.0
license: Apache-2.0
extends: binarya/base_project@1.0.0
lineage:
  forked_from: binarya/software_project@2.0.0
dependencies:
  - coordinate: binarya/base_project@1.0.0
    checksum: sha256:...
```

`extends` is structural. `lineage` is attribution. If `extends` names a pack it
must also appear in the exact dependency closure unless it resolves to a
packaged compatibility seed.

## Deterministic Artifact

The portable artifact is a ZIP with:

- lexicographically sorted entries;
- normalized `/` paths;
- fixed timestamp `1980-01-01T00:00:00`;
- fixed non-executable file mode;
- canonical UTF-8/LF content;
- no directory entries, links or extra metadata.

YAML is parsed and emitted through the existing structured serializer before
packaging. Markdown examples normalize line endings only. SHA-256 of archive
bytes is the artifact checksum. The existing normalized effective-pack hash is
the semantic checksum.

Archive inspection reads bounded bytes directly and does not extract before all
entry, type, link, path and size checks pass. Limits are part of the schema
command so callers can preflight artifacts.

## Installation Layout And Resolution

Portable versions are stored side by side under:

```text
.p2p/project/verticals/_portable/<publisher>/<id>/<version>/
```

The project vertical scanner becomes recursive. Legacy one-level project packs
retain current precedence and bare-ID behavior. Portable callers use exact
coordinates; ambiguity is an error, never a newest-version choice.

Installation preview computes candidate files, exact dependencies, conflicts,
checksums and a mutation token bound to current relevant state. Apply
recomputes preview, verifies token and confirmation, then writes all candidate
files through the existing `AtomicMutationWriter` while holding its durable
per-project workspace-mutation lock.

## Adoption And Migration

Adoption uses the existing deterministic vertical selection renderer only when
the current definition has no meaningful owner evidence.

Migration computes an explicit impact model:

- same section and field ID: preserve value and provenance;
- explicit source-to-target mapping: preserve into the named target;
- no target: append an orphan containing source path, value, provenance and
  migration coordinate;
- ambiguous, missing or duplicate mapping: blocker;
- no fuzzy matching.

Section assumptions, questions and blockers without a compatible destination
are also represented as structured orphans. Existing proposal/question
artifacts remain governed by their current services; migration does not rewrite
or delete them.

The operation commits active vertical metadata, lock, definition state and
migration history as one atomic candidate. Post-render validation runs before
commit. A failed validation or write leaves the previous complete state intact.

## Preview Tokens And Locking

Use the existing `MutationPreviewService` token contract. Tokens include the
operation name, normalized request, relevant current file digests and candidate
impact. No token is issued for a blocked preview.

Use the existing durable workspace transaction lock rather than introducing a
second lock domain. It serializes vertical writes with every other governed
workspace mutation, persists a rollback journal and exposes explicit stale or
recovery-owned states. A non-blocking acquisition failure maps to
`project_busy`.

## CLI Surface

```text
p2p project vertical schema --format json
p2p project vertical scaffold TARGET [--extends COORDINATE]
p2p project vertical inspect TARGET --view declared|effective
p2p project vertical package TARGET --output FILE
p2p project vertical install preview ARTIFACT --expected-checksum SHA256
p2p project vertical install apply ARTIFACT --expected-checksum SHA256 \
  --token TOKEN --confirm --actor ACTOR
p2p project vertical adopt preview COORDINATE
p2p project vertical adopt apply COORDINATE --token TOKEN --confirm --actor ACTOR
p2p project vertical migrate preview COORDINATE [--mapping FILE]
p2p project vertical migrate apply COORDINATE [--mapping FILE] \
  --token TOKEN --confirm --actor ACTOR
p2p init ... --vertical-pack ARTIFACT --expected-checksum SHA256
```

Success and failure JSON use one additive envelope. Existing vertical commands
keep their present payloads for compatibility; only the new commands require
the envelope.

## Compatibility And Rollout

1. Add models and tests without changing v1 behavior.
2. Add safe package read/write and exact-coordinate resolution.
3. Add install preview/apply.
4. Add init integration.
5. Add adoption and migration.
6. Update docs and release packaging checks.

MCP mutation parity is intentionally deferred. The lifecycle services accept
typed inputs and return serializable results so a later MCP adapter does not
duplicate domain logic.

## Failure Policy

- Unsafe input fails before any extraction or mutation.
- Checksum and coordinate mismatches fail closed.
- Missing dependency artifacts fail closed; P2P never downloads them.
- Existing-coordinate checksum conflicts fail closed.
- Stale preview, missing confirmation and concurrent mutation fail closed.
- Migration evidence is preserved or explicitly orphaned, never dropped.
