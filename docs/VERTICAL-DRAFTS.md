# Vertical Draft Authoring V1

P2P Engine separates mutable vertical authoring from immutable vertical
releases. WaveKit and other callers edit one normalized document; P2P Engine
alone compiles canonical `manifest.yml`, `vertical.yml`, `sections/*.yml` and
the other schema-3 files.

```text
normalized draft -> materialized pack -> validation -> .p2pv package
                 -> immutable local add -> optional registry publication
```

## Storage Boundary

Drafts are user-level authoring state. They are stored under
`$P2P_HOME/vertical-drafts/<draft-id>/` when `P2P_HOME` is configured, or under
the platform user-data directory. They never live in project `.p2p` memory and
never acquire the project workspace lock.

Each draft contains:

- `draft.yml`: ID, revision, document hash, origin and normalized document;
- `evidence.yml`: current materialization, validation, package, local-add and
  publication evidence;
- a per-draft mutation lock used only while changing that draft.

Every update requires an expected revision or document hash. A successful edit
increments the revision and clears all downstream evidence.

## Normalized Document

The independent document contract is `p2p-vertical-draft/v1`. Its root fields
are:

```yaml
contract_version: p2p-vertical-draft/v1
identity:
  publisher: example
  id: software-blue
  version: 1.0.0
  license: MIT
name: Software Blue
description: A software project vertical.
visibility: private
domain_metadata:
  primary_domain: null
  domain_tags: []
extends: null
lineage:
  forked_from: null
  previous_release: null
dependencies: []
sections: []
rubrics: []
questions: []
artifacts: []
profiles:
  enabled: []
  definitions: []
modules:
  enabled: []
  definitions: []
examples: []
source_attribution: {}
compatibility: {}
```

References use an exact coordinate and semantic checksum. `extends` describes
structural composition. `lineage.forked_from` records a social derivation.
`lineage.previous_release` connects immutable versions of the same authored
vertical. None is inferred from another.

`domain_metadata.primary_domain` and `domain_metadata.domain_tags` are optional
advisory catalog metadata. They do not select structure or change the domain of
projects that adopt the release.

An empty draft intentionally has no sections, readiness 0 and no placeholder
content. It cannot be materialized, packaged, selected or published until it
has a valid identity and at least one governed section.

## CLI Lifecycle

Create an empty draft:

```bash
p2p vertical draft create --empty --format json
```

Clone exact effective content and declare a new release identity:

```bash
p2p vertical draft create \
  --from binarya/software_project@2.0.0 \
  --version 2.0.1 \
  --previous-release binarya/software_project@2.0.0 \
  --format json
```

Inspect and replace the complete normalized document:

```bash
p2p vertical draft inspect VDRAFT-... --format json
p2p vertical draft update VDRAFT-... \
  --document ./vertical-document.json \
  --expected-revision 1 \
  --format json
```

Compile and verify a release:

```bash
p2p vertical draft materialize VDRAFT-... ./build/software-blue --format json
p2p vertical draft validate VDRAFT-... --format json
p2p vertical draft package VDRAFT-... ./build/software-blue.p2pv --format json
```

Add the exact artifact to the immutable user catalog or publish it:

```bash
p2p vertical draft add-local VDRAFT-... --format json
p2p vertical draft publish VDRAFT-... \
  --registry wavekit \
  --idempotency-key <caller-operation-id> \
  --format json
```

`add-local` is idempotent for identical bytes and fails if the coordinate
already identifies different immutable content. `publish` never repackages;
it uploads the exact artifact recorded in current evidence.

## WaveKit Contract

All eight commands support `p2p-cli/v1` JSON envelopes. The document, draft
state and evidence retain their own versions. WaveKit should persist the draft
ID, revision and document hash and send the complete normalized document with
an optimistic precondition on every update.

Direct draft MCP tools are intentionally absent. A server-side
WaveKit worker invokes this CLI through its serialized operation path. Existing
MCP proposal creation still shares the core no-target-section guard with the
CLI and fails with `P2P_VERTICAL_NO_TARGET_SECTION` when no valid active
section exists.
