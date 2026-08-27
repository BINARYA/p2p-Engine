# Project Structure Surface Convergence

This is the P2P Engine 0.5.0 release-gate note for converging the project-owned
structure surfaces after authority, domain, memory classification, readiness,
registry-v2 discovery, structure export and structure replacement landed.

The executable inventory lives in
`p2p_engine.services.release_convergence`. The packaged WaveKit-facing CLI
fixture bundle lives at
`p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json`.

## Current Contract Tuple

`p2p version --format json`, `p2p status --format json` and
`p2p_workspace_schema_status` expose the same contract tuple:

- P2P Engine `0.5.0`
- CLI envelope `p2p-cli/v1`
- workspace schema 4
- portable vertical schema 3 and package format 1
- vertical registry protocol `p2p-vertical-registry/v2`
- vertical draft document/state/evidence v1
- project domain, structure, memory classification, readiness and receipt
  contract versions
- project authority and AuthorityContext schemas

## Convergence Matrix

| Operation | Capability | CLI | MCP decision | Receipt evidence | Hosted boundary |
| --- | --- | --- | --- | --- | --- |
| `project.initialize` | `project.initialize` | `p2p init` | `p2p_init_project` | schema-3 mutation receipt when keyed | Hosted services enforce access; P2P records neutral authority evidence. |
| `project.authority.rotate` | `project.authority.rotate` | authority rotate preview/apply/status | CLI-only authority admin | schema-3 receipt | Rotation changes project authority metadata, not provider policy. |
| `project.domain.change` | `project.domain.change` | domain show/set/clear | same domain service | schema-3 receipt | Domain classification cannot choose structure or grant moderation. |
| `project.structure.edit` | `project.structure.edit` | structure show/history/add/update/reorder | same structure service | schema-3 receipt plus structure event | Ordinary edits never require active vertical lock or release mutation. |
| `project.memory.classify` | `project.memory.classify` | memory classification and proposal scope | same memory-scope service | schema-3 receipt plus memory-scope event | Scope organizes memory only and cannot decide proposals. |
| `proposal.readiness.assess` | `proposal.readiness.assess` | proposal readiness assess | same advisory semantics | schema-3 receipt for keyed CLI worker apply | Assessment never accepts, rejects or overrides decisions. |
| `project.readiness.review` | read-only | project readiness review/gaps/questions | same read-only service | not applicable | Retired/origin criteria and classification debt are excluded from score. |
| `project.structure.retire` | `project.structure.retire` | retirement preview/apply/status | same retirement preview/apply service | schema-3 receipt plus retirement result | Disposition plan governs memory movement without using history as source. |
| `vertical.remote.discovery` | read-only | registry-v2 domain/list/search reads | same registry-v2 read services | not applicable | Provider-neutral discovery cannot imply project authority. |
| `vertical.remote.obtain` | read-only | `p2p vertical pull` | CLI-only user cache write | immutable cache metadata | Pull writes user cache only, not project state. |
| `project.vertical.export` | `project.vertical.export` | export eligibility/preview/apply | MCP eligibility/preview only | schema-3 receipt plus export marker/result | Authority does not grant publisher ownership, remote publication or moderation rights. |
| `project.structure.replace` | `project.structure.replace` | replacement preview/apply/status | MCP inspect/preview only | schema-3 receipt plus replacement result | Replacement copies one exact release; it is not adopt, migrate, pull or subscription. |
| `proposal.create` | `proposal.create` | proposal create/list/show | same proposal service | schema-3 receipt for keyed CLI worker writes | Creation records explicit unassigned scope and no decision authority. |
| `proposal.update` | `proposal.update` | proposal update/show | same proposal service | schema-3 receipt for keyed CLI worker writes | Updates do not decide or change implementation state. |
| `proposal.contribution.add` | `proposal.contribution.add` | contribution add/list | same contribution service | schema-3 receipt for keyed CLI worker writes | Proposal memory does not imply implementation, membership or governance decision. |
| `proposal.decide` | `proposal.decide` | decision preview/apply/status/history/impact | same consent-gated decision service | append-only event plus typed AuthorityContext | Decision and readiness override are separate grants. |
| `project.vertical.install` | `project.vertical.install` | install preview/apply | CLI-only vertical lifecycle | schema-3 receipt | Install adds one exact release without making it authoritative structure. |
| `project.vertical.adopt` | `project.vertical.adopt` | adopt preview/apply | CLI-only vertical lifecycle | schema-3 receipt | Adopt affects release metadata, not detached project structure. |
| `project.vertical.migrate` | `project.vertical.migrate` | migrate preview/apply | CLI-only vertical lifecycle | schema-3 receipt | Migration preserves evidence by exact mapping and does not replace structure. |
| `project.structure.merge_restore` | `project.structure.merge` | none | deferred | deferred | Explicit post-0.5.0 deferral; not an available operation in this release. |

## WaveKit Fixture

The WaveKit-facing CLI fixture bundle is deterministic and sanitized. It covers
startup probes, read commands, registry-v2 reads, retryable writes and recovery:

- `p2p version --format json`
- `p2p status --format json`
- `p2p project structure show --format json`
- `p2p project vertical export eligibility --format json`
- `p2p project vertical export apply ... --idempotency-key wavekit:<uuid>`
- `p2p project structure replace apply ... --operation-key wavekit:<uuid>`
- `p2p vertical domain list/search/inspect --registry REGISTRY --format json`
- `p2p vertical search/list ... --domain DOMAIN-ID --format json`
- `p2p mutation status --operation-key wavekit:<uuid> --format json`

It uses neutral placeholders such as `PROJECT-AUTHORITY-ID`, `ACTOR`,
`EXECUTOR`, `REGISTRY`, `DOMAIN-ID`, `TOKEN`, `SHA256` and `wavekit:<uuid>`.
It contains no local roots, user names, credentials or provider roles.

## MCP Deferrals

MCP remains protocol-native and is not wrapped in `p2p-cli/v1`. It exposes
read-only eligibility or preview where that is the safe local agent surface.
There is no MCP tool for project-structure export apply, package destination
selection, structure replacement apply, remote publication, registry login or
pull. Those operations stay on CLI JSON with explicit actor, confirmation,
source preconditions and idempotency key.

## Registry V2

Current remote registry discovery uses `p2p-vertical-registry/v2`. Domain list,
domain search, domain inspect and domain-filtered release list/search are
provider-neutral reads. Protocol-v1 references remain only in bounded tests
that prove deterministic rejection. There is no executable protocol-v1
fallback in the runtime catalog client.

## Release Notes And Resources

The release notes state a clean break: P2P Engine 0.5.0 supports workspace
schema 4 and portable vertical schema 3 only. It does not provide in-runtime
migration, conversion or compatibility aliases for older workspace or vertical
schemas.

Required packaged resources include all bundled vertical releases, release
contract inventory code, the convergence gate service, and the WaveKit CLI
fixture JSON. `scripts/verify-release-artifacts.py` verifies those resources
inside both wheel and sdist. `scripts/verify-convergence-gate.py` verifies that
the packaged fixture matches the installed runtime generator.

## CI And Residual Risk

The release workflow runs the source public/full suites across Python 3.11 and
3.14, then builds artifacts in one dedicated release job, verifies archive
contents and runs installed-wheel smoke tests. Matrix jobs do not upload or
share release assets.

The only recorded non-blocking deferral is `project.structure.merge_restore`.
It remains unavailable until its own feature adds domain behavior, surfaces,
fixtures and a later convergence audit.
