# Design - Separate Domain From Structure Source

## Requirements Covered

- R001-R027
- N001-N005
- AC001-AC009

## Decision Summary

Introduce `ProjectDomainRef` and `StructureSource` as separate core contracts.
The free project domain is classification only. Initialization resolves one
starter or one exact vertical release and delegates materialization to the
project-owned structure feature. The change is current-only and participates
in the coordinated workspace schema 4 and P2P Engine `0.5.0` release.

## Key Decisions

### D001 - Domain Is A Project Reference, Not A Catalog Entity

`ProjectDomainRef` contains `key`, `name`, `source` and `external_ref`. P2P
validates and persists the descriptor but does not own publishers, permissions,
visibility, moderation or ranking. A vertical pack may repeat a primary domain
reference for portable discovery, but that metadata is advisory.

### D002 - Structure Source Is A Closed Tagged Union

The logical contract is:

```json
{"kind": "starter", "starter_id": "generic"}
```

or:

```json
{
  "kind": "vertical_release",
  "coordinate": "publisher/id@1.0.0",
  "checksum": "sha256"
}
```

`empty` is a starter identifier. Installed and supplied packs converge to the
same exact vertical-release identity before initialization. CLI parsing cannot
construct two union members.

### D003 - Specialized Built-ins Are Ordinary Releases

Software, board-game, grant-document and comparable presets ship as bundled
schema-3 vertical releases. This keeps one reusable structural abstraction and
prevents a parallel starter catalog. Only `generic` and `empty` remain system
starters because they have cross-domain initialization semantics and are
excluded from social lineage metrics.

### D004 - Domain Mutation Uses Existing Receipt Infrastructure

Domain set and clear are atomic one-project mutations. The semantic fingerprint
binds actor, operation key, prior project identity and normalized descriptor.
The public result reports logical before/after values and revisions, never
physical artifact names. Local MCP consent calls the same service.

### D005 - Current-Only Schema Transition

Workspace schema 4 gives `domain` the new meaning and records normalized
structure-source provenance. Runtime code contains no adapter that converts
schema-3 domain rubrics. Existing projects are recreated or converted by an
explicit external one-time tool outside the runtime support path.

### D006 - Version The Domain Payload, Not The Global Envelope

The global CLI envelope remains `p2p-cli/v1`. Initialization and domain reads
publish domain payload contract `p2p-project-domain/v1`; initialization
publishes the new project-init domain payload version chosen during P2/P9
convergence.

### D007 - Capability Is Declared, Provider Policy Is External

Initialization declares `project.initialize`; domain set/clear declare
`project.domain.change`. Both consume the shared AuthorityContext and bind it to
mutation identity. Local P2P policy resolves standalone owner authority. An
external provider may impose a stricter delegation policy, but no WaveKit role
or grant table enters these core services.

## Components And Ownership

- Core: typed domain descriptor, structure-source union and serializers.
- Initialization service: argument normalization, exclusive-source validation
  and delegation to project-structure materialization.
- Project domain service: show, preview/apply mutation and receipt replay.
- Portable vertical model: optional primary domain reference and tags.
- CLI: free domain options, explicit starter/vertical source and structured
  domain commands.
- MCP: domain read and consent-gated mutation handlers.
- Agent capabilities/templates: terminology and standalone workflows.

## Error And Recovery Model

Validation errors occur before candidate creation. Atomic writes use the
workspace lock, source preconditions and durable receipts. A lost response is
resolved by exact retry or mutation status. Unsupported workspace schemas fail
before any domain read is represented as current.

## Alternatives Considered

- Keep old domain templates and ignore them when a pack is present: rejected
  because two structural concepts and unresolved domain state would remain.
- Make domains a local global catalog: rejected because ownership and discovery
  belong to optional providers such as WaveKit.
- Treat every built-in as a starter: rejected because it recreates a second
  structural package system.

## Migration And Compatibility

- Target release: `0.5.0`.
- Target workspace schema: `4`.
- Target vertical pack schema: `3`, coordinated with readiness criteria.
- No runtime compatibility for schema 3 project memory.
- Remote domain discovery is owned by
  `extend-remote-registry-client-with-domain-discovery`, implemented after this
  core domain contract and before the 0.5.0 convergence gate. Local packs
  remain offline-first and initialization never performs implicit discovery.
