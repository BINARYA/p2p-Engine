# Design - Extend Remote Registry Client With Domain Discovery

## Requirements Covered

- R001-R023
- N001-N005
- AC001-AC008

## Decision Summary

Replace the current registry-v1 client contract with a current-only v2
contract that adds domain catalog endpoints and domain classification on
vertical releases. Reuse the existing transport, secure credentials and
vertical catalog services. Keep every domain response advisory and terminate
remote access at typed metadata; project initialization still resolves one
explicit local starter or verified exact release.

## Key Decisions

### D001 - Protocol V2 Is A Clean Current Contract

The well-known path remains `/.well-known/p2p-vertical-registry`, while the
capability payload declares `p2p-vertical-registry/v2`. Required endpoint keys
are `domains`, `domain`, `search`, `releases` and `release`; `publish` and
OAuth Device Flow remain optional under their existing rules. P2P 0.5 does not
carry a registry-v1 compatibility parser.

### D002 - One Typed Catalog Domain

`RegistryDomain` contains bounded external ID, key, display metadata,
visibility, lifecycle, optional publisher and optional
`RecommendedVerticalRelease`. It deliberately has no structure payload. The
project's `ProjectDomainRef` may record a selected provider reference, but the
remote catalog object is not copied into canonical project memory by a read.

### D003 - Vertical Classification Is Nullable And Advisory

`VerticalRelease` gains an optional primary-domain reference. It does not enter
artifact checksum, dependency closure or exact-coordinate identity. Search may
filter by the provider's opaque domain ID; resolution and pull continue to use
the existing exact release services.

### D004 - Bounded Pagination Lives In The Service

The HTTP adapter performs one request. A registry query service follows only
the preceding validated cursor, with page size at most 100 and at most 10
pages. It rejects repeated cursors and conflicting duplicates. CLI/MCP may
request one page or the bounded aggregate but cannot submit provider URLs.

### D005 - Existing Device Flow Is The Only Private Credential Path

Domain reads reuse the registry read scope, token refresh and keyring adapter.
The capability document does not introduce command-line token arguments.
Uniform inaccessible/not-found mapping is preserved for private detail.

### D006 - MCP Parity Is Read-Only

Local MCP exposes only domain catalog reads and domain-filtered vertical
search, using the same service and network-read permission class. Login,
logout, pull and publish remain CLI/service workflows until separately
specified consent contracts exist.

## Components And Ownership

- `core/vertical_registry.py`: v2 capabilities, domain, pagination and updated
  release metadata contracts.
- `services/vertical_registry.py`: domain queries, domain-filtered release
  queries, credential and pagination policy.
- `adapters/vertical_registry_http.py`: unchanged bounded same-origin transport.
- `cli_commands/verticals.py`: domain list/search/inspect and exact filter
  presentation.
- MCP catalog/handlers: read-only wrappers over registry services.
- Agent capabilities/templates and registry documentation: accurate supported
  workflows and advisory semantics.

## Public Protocol Shape

The provider advertises relative or same-origin endpoint templates under the
existing capability document. Logical responses are:

```text
vertical_domains:
  protocol_version: p2p-vertical-registry/v2
  items: [RegistryDomain]
  page: {returned, next_cursor, truncated}

vertical_domain:
  protocol_version: p2p-vertical-registry/v2
  domain: RegistryDomain

vertical_releases:
  protocol_version: p2p-vertical-registry/v2
  items: [VerticalRelease including optional primary_domain]
  page: {returned, next_cursor, truncated}
```

Exact route strings are provider-advertised. The P2P client owns endpoint
template validation and never embeds WaveKit paths.

## Failure And Recovery Model

Catalog reads are side-effect free. A failed page invalidates the aggregate
result and does not overwrite a previously negotiated valid capability record
with partial data. Credential refresh follows existing exact rules. No project
lock or mutation receipt is created. Existing immutable artifact cache remains
unchanged until a separate explicit pull.

## Alternatives Considered

- Add optional fields to protocol v1: rejected because current development has
  no compatibility requirement and v2 prevents old clients from silently
  misreading domain-aware pagination.
- Put domains inside vertical packs: rejected because catalog ownership,
  visibility and recommendations are provider metadata.
- Let init accept a domain and choose its recommendation automatically:
  rejected because structure-source selection must remain explicit and frozen.
- Add MCP pull/login at the same time: rejected because those operations need a
  separate side-effect and consent design.

## Compatibility

This feature is included before the P2P Engine 0.5.0 release gate. Registry v1
configuration/capabilities are unsupported by the current runtime and must be
refreshed against a v2 provider. Local bundled/cached exact-release workflows
remain available offline and unchanged except for schema-3 pack validation.

