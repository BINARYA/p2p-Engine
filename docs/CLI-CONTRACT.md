# CLI JSON Contract

P2P Engine 0.6.4 exposes one machine-facing CLI transport contract:
`p2p-cli/v1`. Every command that accepts `--format json`, including commands
whose format defaults to JSON, emits exactly one JSON document to stdout.

## Envelope

Successful response:

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": true,
  "operation": "project.vertical.list",
  "data": {},
  "warnings": [],
  "error": null
}
```

Failed response:

```json
{
  "contract_version": "p2p-cli/v1",
  "ok": false,
  "operation": "project.vertical.show",
  "data": null,
  "warnings": [],
  "error": {
    "code": "P2P_VERTICAL_AMBIGUOUS_REFERENCE",
    "message": "The vertical reference is ambiguous.",
    "details": {}
  }
}
```

The top level contains only `contract_version`, `ok`, `operation`, `data`,
`warnings` and `error`. Domain-specific fields are under `data` on success and
typed diagnostic context is under `error.details` on failure.

`operation` is the invoked command path joined by dots. For example,
`p2p project vertical install preview` reports
`project.vertical.install.preview`. This identifier does not depend on the
human-readable message or payload fields.

## Exit Classes

| Exit | Meaning |
| ---: | --- |
| 0 | Success |
| 1 | Internal or otherwise unclassified failure |
| 2 | Invalid option, argument, type or request |
| 3 | Conflict or failed precondition |
| 4 | Authentication, authorization or consent failure |
| 5 | Unavailable dependency, registry or transport |

Consumers must branch on `ok`, `error.code` and the exit class. They must not
infer behavior from `error.message`.

When JSON is requested, missing arguments, unknown options and conversion
errors use the same envelope with `P2P_CLI_INVALID_REQUEST`. Text mode retains
Typer/Rich help and error rendering.

## Consumer Integration

Consumers that bypass the current envelope and read domain fields directly are
unsupported:

```python
payload["project_readiness"]
```

The current form is:

```python
envelope = json.loads(stdout)
if not envelope["ok"]:
    raise RuntimeError(envelope["error"]["code"])
payload = envelope["data"]
project_readiness = payload["project_readiness"]
```

WaveKit should deserialize the six transport fields first, validate
`contract_version == "p2p-cli/v1"`, and then dispatch `data` by `operation`.
Parser failures are JSON and therefore do not require a separate stderr parser.

MCP responses are protocol-native and are not wrapped in `p2p-cli/v1`.

`p2p version --format json` returns the complete release contract tuple.
`p2p status --format json` returns the same tuple under
`data.contract_versions` beside the read-only workspace status. The tuple
includes engine, CLI envelope, workspace schema, portable vertical schema,
portable package format, registry protocol, registry config, vertical draft,
project-domain, project-structure, project-memory, readiness, AuthorityContext
and mutation-receipt contract versions.

## Governed Authority Input

Schema-4 governed mutations declare a capability from the public registry:

```bash
p2p project authority capabilities --format json
p2p project authority show --format json --root /project
```

Implemented external-attestation mutations accept an allowlisted
`p2p-authority-context/v1` JSON file through `--authority-context`. The file is
parsed as a closed, bounded contract; arbitrary provider payloads and
shell-expanded JSON are not supported. Project initialization, generic
proposal decision preview/apply, simple project-structure edits and authority
rotation, and project-memory scope assignment are the integrated CLI surfaces.
Existing proposal-authoring and vertical mutations remain explicitly
`existing_unintegrated` and local-policy only until their own feature adopts
the shared authority contract.

The context digest is part of preview and idempotency identity. An exact retry
must resubmit the same context and returns the original receipt without a new
authorization check. A changed subject, executor, claim basis, grant
generation or provider policy is a different request and fails closed. See
[AUTHORITY-CONTEXT.md](AUTHORITY-CONTEXT.md) for the trust boundary and full
examples.

## WaveKit Worker Contract

WaveKit's serialized P2P worker consumes an allowlisted subset of CLI JSON
commands. It must not parse human output, inspect `.p2p` files, import
`p2p_engine` internals, or use local MCP stdio as its deterministic retry
transport.

Startup and recovery probes:

```bash
p2p version --format json
p2p status --format json
p2p runtime status --format json
p2p workspace schema status --format json
p2p workspace transaction status --format json
```

Project and proposal reads:

```bash
p2p project snapshot --format json
p2p project domain show --format json
p2p project structure show --format json
p2p project structure history --limit 20 --format json
p2p project vertical export eligibility --format json
p2p project memory classification --format json
p2p proposal list --format json
p2p proposal show PROP-001 --format json
p2p proposal scope show PROP-001 --format json
p2p proposal contribution list PROP-001 --type suggestion --format json
```

Registry-v2 reads are provider-neutral and advisory. They can perform explicit
remote network reads, but they do not prove compatibility, pull artifacts,
initialize projects, change structure or grant publisher/moderation rights:

```bash
p2p vertical domain list --registry REGISTRY --format json
p2p vertical domain search software --registry REGISTRY --format json
p2p vertical domain inspect DOMAIN-ID --registry REGISTRY --format json
p2p vertical search software --registry REGISTRY --domain DOMAIN-ID --format json
p2p vertical list --source remote --registry REGISTRY --domain DOMAIN-ID --format json
```

WaveKit-facing writes use its persisted operation identity:

```bash
p2p init "Project name" --starter generic --format json --operation-key wavekit:<uuid>
p2p init "Software" --domain software --vertical binarya/software_project@2.0.0 --format json --operation-key wavekit:<uuid>
p2p project domain set gardening --name "Gardening" --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p project domain clear --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p project structure add-section "Distribution" --expected-revision REV --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p project structure update-metadata section distribution --title "Distribution model" --expected-revision REV --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p project structure reorder --section-id distribution --section-id scope --expected-revision REV --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p project structure retire preview --target section:distribution --expected-structure-revision REV --expected-memory-revision SHA256 --plan retirement-plan.yml --actor ACTOR --format json
p2p project structure retire apply --target section:distribution --expected-structure-revision REV --expected-memory-revision SHA256 --preview-token TOKEN --operation-key wavekit:<uuid> --plan retirement-plan.yml --actor ACTOR --confirm --format json
p2p project structure retire status --operation-key wavekit:<uuid> --format json
p2p project structure replace preview publisher/vertical_id@1.0.0 --expected-structure-revision REV --expected-memory-revision SHA256 --plan replacement-plan.yml --actor ACTOR --format json
p2p project structure replace apply publisher/vertical_id@1.0.0 --expected-structure-revision REV --expected-memory-revision SHA256 --preview-token TOKEN --operation-key wavekit:<uuid> --plan replacement-plan.yml --actor ACTOR --confirm --format json
p2p project structure replace status --operation-key wavekit:<uuid> --format json
p2p project structure merge compare publisher/vertical_id@1.0.0 --select section:scope --format json
p2p project structure merge preview publisher/vertical_id@1.0.0 --plan merge-plan.yml --actor ACTOR --format json
p2p project structure merge apply publisher/vertical_id@1.0.0 --plan merge-plan.yml --preview-token TOKEN --operation-key wavekit:<uuid> --actor ACTOR --confirm --format json
p2p project structure merge status --operation-key wavekit:<uuid> --format json
p2p project structure retained list --format json
p2p project structure retained inspect REVISION --format json
p2p project structure restore preview --plan restore-plan.yml --actor ACTOR --format json
p2p project structure restore apply --plan restore-plan.yml --preview-token TOKEN --operation-key wavekit:<uuid> --actor ACTOR --confirm --format json
p2p project structure restore status --operation-key wavekit:<uuid> --format json
p2p project vertical export eligibility --format json
p2p project vertical export preview --publisher publisher --id vertical_id --version 1.0.0 --name "Vertical" --license MIT --primary-domain-key software --primary-domain-name "Software" --lineage-mode independent --format json
p2p project vertical export apply --target build/vertical --output dist/vertical.p2pv --publisher publisher --id vertical_id --version 1.0.0 --name "Vertical" --license MIT --primary-domain-key software --primary-domain-name "Software" --lineage-mode independent --expected-structure-revision REV --expected-structure-checksum SHA256 --token TOKEN --idempotency-key wavekit:<uuid> --confirm --format json
p2p proposal create "Title" --proposal "..." --format json --operation-key wavekit:<uuid>
p2p proposal scope set PROP-001 --kind sections --section-id distribution --expected-memory-revision SHA256 --expected-structure-revision REV --actor ACTOR --format json --operation-key wavekit:<uuid>
p2p proposal update PROP-001 --proposal "..." --format json --operation-key wavekit:<uuid>
p2p proposal contribution add PROP-001 "Text" --type finding --format json --operation-key wavekit:<uuid>
p2p proposal readiness assess PROP-001 --actor ACTOR --format json --operation-key wavekit:<uuid>
```

An exact retry with the same operation key and the same semantic request returns
`already_applied`. Reusing the same key for different semantic inputs fails with
`P2P_IDEMPOTENCY_CONFLICT`.

Proposal creation records explicit `unassigned` scope. Accepting or reinstating
a proposal requires one or more active sections or explicit `project_global`
scope. Scope mutation uses capability `project.memory.classify` and cannot
authorize `proposal.decide` or `proposal.readiness.override`. The
`p2p-memory-classification/v1` read model reports organization only and always
declares `readiness_effect: none`.

After a lost or uncertain response:

```bash
p2p mutation status --operation-key wavekit:<uuid> --format json
```

The status payload classifies the supplied key as `wavekit_uuid`,
`p2p_operation`, `wavekit_opaque`, or `opaque`, and sets
`raw_value_returned: false`. It never echoes the raw key.

Proposal readiness, artifact state and proposal-question summaries needed by
WaveKit are available through `data.proposal_detail` from
`p2p proposal show PROP --format json`. Its readiness object includes
`freshness` (`not_assessed`, `current` or `stale`), the assessment policy
version, the stored source fingerprint and the current source fingerprint.
Reading freshness never writes project state. WaveKit should use this bounded
read model for UI detail pages and enqueue a recalculation only when explicitly
requested.

The keyed readiness command commits `readiness.yml` and its receipt in one
workspace transaction. Its operation is `proposal.readiness.assess`; success
data contains `proposal_readiness_assess` and `mutation`. Exact retry returns
`already_applied`, while later proposal-evidence changes make the read model
`stale` without invalidating the historical receipt. The assessment is
advisory: it does not accept, reject, defer, override or otherwise decide the
proposal.

Human/local use remains valid without an operation key:

```bash
p2p proposal readiness assess PROP-001
```

Local MCP exposes the same atomic assessment semantics through
`p2p_proposal_readiness_assess`, but its response remains protocol-native and
does not implement the WaveKit CLI receipt envelope.

The deterministic worker fixture for this release is packaged as
`p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json`. It is generated
from the current agent policy and validated by the convergence gate; workers
can compare it with the installed runtime without reading P2P internals.

Overall project definition completeness is a separate derived, read-only
surface. Use `project snapshot`, `project progress` or `project readiness`
reads; do not confuse them with proposal readiness or the operational
`p2p assess refresh` artifact.

## Idempotent Vertical Mutations

The three vertical apply commands require an opaque caller key in addition to
the preview token, actor and explicit confirmation:

```text
--idempotency-key <operation-uuid>
```

WaveKit should use its persisted operation UUID. P2P stores only its SHA-256
hash and commits the success receipt in the same atomic workspace transaction
as the vertical mutation. An exact retry returns `already_applied` without
writing again. Reusing the key with a changed actor, token, coordinate,
checksum, profile, modules or transition plan fails with
`P2P_IDEMPOTENCY_CONFLICT`.
Changed committed files fail with `P2P_IDEMPOTENCY_POSTCONDITION_DRIFT`.

After a lost or uncertain response, inspect the redacted result with:

```bash
p2p mutation status \
  --operation-key <operation-uuid> \
  --root <project-root> \
  --format json
```

The successful lookup states are `not_found`, `applied`,
`postcondition_drift` and `incomplete`. An incomplete state requires the
existing `p2p workspace transaction status|resume|rollback` workflow. A
malformed or inconsistent receipt is a typed
`P2P_IDEMPOTENCY_RECEIPT_CORRUPT` failure. Status output never includes the raw
key, request payload, preview token, physical project paths or per-file hashes.

## Typed Vertical Transition Impact

Vertical install, adopt and migrate previews expose distinct typed payloads at
`data.impact`. All use:

```text
impact.contract_version = p2p-vertical-transition-impact/v1
```

Every collection has exactly `total`, `returned`, `truncated` and `items`.
The per-collection limit is 128 items and the material transition limit is 512
items. Truncation is fail-closed with
`P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED`; it never hides an apply effect.

Adoption and migration share `source_state`, whose classification is `empty`
only when definition fields, assumptions, blockers, definition orphans, owner
question evidence and rubric customizations all have count zero. Untouched
generated questions and unchanged default rubrics do not populate a project.

Migration is a two-preview workflow. First run without `--mapping`. When
`required_decisions.total` is non-zero, the preview is successful but blocked:
`apply_allowed` is false, `preview` is null and every decision is returned with
a stable ID and exact domain source reference. Supply a complete plan:

```yaml
vertical_transition_plan:
  schema_version: 1
  contract_version: p2p-vertical-transition-plan/v1
  analysis_fingerprint_sha256: <preview analysis fingerprint>
  decisions:
    - id: VTD-0123456789abcdef
      action: map
      source:
        kind: definition_field
        ref: definition_field:legacy.constraints
      target:
        kind: definition_field
        ref: definition_field:constraints.summary
    - id: VTD-fedcba9876543210
      action: preserve_as_orphan
      source:
        kind: rubric
        ref: rubric:legacy_delivery
```

The plan must contain every required decision and no extras. `map` requires one
exact compatible target; `preserve_as_orphan` forbids a target. Duplicate YAML
keys, old `field_mapping`/`rubric_mapping` forms, stale analysis fingerprints,
unknown fields, fuzzy targets and duplicate target ownership are rejected.
Re-preview with the plan and use only the new token for apply.

The public preview summary contains only operation identity, actor, authority,
confirmation policy, apply eligibility and the opaque token. Generic mutation
targets, source preconditions, candidate hashes, token context and internal
paths stay private. Apply and mutation status return typed semantic
postconditions; physical postconditions remain internal to receipt drift
detection.

Install postconditions contain `installed_coordinate`,
`installed_semantic_checksum` and `installed_artifact_checksum`; installation
does not claim to activate the pack. Adoption and migration postconditions
contain `active_coordinate` plus lock, definition, question and rubric semantic
hashes. Structure replacement postconditions contain the detached target
coordinate/checksum, previous/current structure identity, memory revision,
replacement event, applied dispositions and `project.structure.replace`
capability. Receipt replay and mutation status preserve the same
operation-specific field set.

Merge postconditions contain one exact source identity/digest, previous and
new structure identity, retained-history evidence, transition event and
`project.structure.merge` capability. Restore uses the same forward-transition
shape with a retained source revision/checksum and the distinct
`project.structure.restore` capability. Public results expose logical changed
entities only; physical receipt postconditions remain private. Exact retries
return `already_applied`, while source, target, plan, memory or authority drift
fails before activation.
