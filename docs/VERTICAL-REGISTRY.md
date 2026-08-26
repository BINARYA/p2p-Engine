# Vertical Registry Protocol V2

P2P Engine can discover advisory catalog domains and exact portable vertical
releases from a provider-neutral HTTP registry. Remote discovery returns
metadata only. Pulling still requires one explicit release coordinate and
project mutation still uses the standard portable-pack install and structure
selection services.

## Client Configuration

Configure one or more named registries:

```bash
p2p vertical registry add wavekit https://registry.example.test --default
p2p vertical registry list
p2p vertical registry list --refresh
```

`--refresh` is the only `registry list` mode that contacts servers. Registry
configuration is stored in `$P2P_HOME/registries.yml` when `P2P_HOME` is set.
Otherwise it uses the platform user-data directory. The immutable artifact
cache uses `$P2P_HOME/cache/verticals` or the platform user-cache directory.
Neither location is created below the current project.

Registry configuration contains no bearer, refresh, device or provider-secret
tokens. Login uses the operating-system credential provider through Python
`keyring`; failure to find a secure backend is reported without a plaintext
fallback.

## Capability Document

The client reads this fixed path relative to the configured origin:

```text
/.well-known/p2p-vertical-registry
```

Example response:

```yaml
vertical_registry:
  protocol_version: p2p-vertical-registry/v2
  api_base: /api/vertical-registry/v2
  max_artifact_bytes: 8388608
  supports_uncategorized_filter: true
  endpoints:
    domains: domains
    domain: domains/{domain_id}
    search: releases/search
    releases: releases
    release: releases/{publisher}/{vertical_id}/{version}
    publish: releases/publish
  oauth_device:
    device_authorization_endpoint: /oauth/device
    token_endpoint: /oauth/token
    client_id: p2p-engine
    scopes:
      - vertical:read
      - vertical:publish
```

P2P Engine 0.5 accepts only `p2p-vertical-registry/v2`. Required endpoint keys
are `domains`, `domain`, `search`, `releases` and `release`; `publish` and
OAuth Device Flow are optional. All advertised URLs must remain on the
configured registry origin. HTTPS is mandatory, except for `localhost`,
`127.0.0.1`, and `::1` development registries explicitly configured with HTTP.

## Domain Documents

List and search return bounded pages:

```yaml
vertical_domains:
  protocol_version: p2p-vertical-registry/v2
  items:
    - external_id: dom-software
      key: software
      name: Software
      description: Software projects
      visibility: public
      lifecycle: active
      publisher: example
      recommended_release:
        coordinate: example/software-blue@1.0.0
        semantic_checksum: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
        artifact_sha256: abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
  page:
    returned: 1
    next_cursor: null
    truncated: false
```

Exact domain detail returns the same `RegistryDomain` under `vertical_domain`.
Domain payloads are advisory catalog metadata. They must not contain sections,
criteria, fields, questions, readiness weights, project memory, tasks, commands
or executable instructions. Unknown optional display metadata is ignored, but
unknown visibility/lifecycle values fail closed.

A recommended release is only an exact coordinate plus immutable digest. It
does not trigger pull, initialization, adoption, migration or project-domain
mutation.

## Release Documents

List and search return bounded pages:

```yaml
vertical_releases:
  protocol_version: p2p-vertical-registry/v2
  items: []
  page:
    returned: 0
    next_cursor: null
    truncated: false
```

An exact release endpoint returns:

```yaml
vertical_release:
  protocol_version: p2p-vertical-registry/v2
  release:
    coordinate: example/software-blue@1.0.0
    name: Software Blue
    description: Example vertical
    visibility: public
    semantic_checksum: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
    schema_version: 3
    primary_domain:
      external_id: dom-software
      key: software
      name: Software
    artifact:
      url: /artifacts/example/software-blue/1.0.0/package.p2pv
      sha256: abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
      size: 4096
    dependencies:
      - coordinate: example/software-base@1.0.0
        semantic_checksum: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
```

Coordinates and dependency coordinates are exact; tags, ranges and implicit
latest-version resolution are not part of protocol v2. Artifact URLs can be
relative or same-origin absolute URLs.

`primary_domain` is nullable advisory discovery metadata. It never selects
project structure, proves semantic compatibility, injects readiness rules, or
replaces the project's independent domain classification.

## Pagination

Domain and release list/search endpoints use stable ordering, `limit`,
`cursor`, opaque cursors and a maximum page size of 100. The P2P client follows
at most 10 pages for one CLI or MCP aggregate read. Count mismatches, repeated
cursors, malformed terminal pages, oversized pages and conflicting duplicate
IDs fail without returning a partial complete result.

## Authentication

Public domain and release discovery works anonymously when the provider permits
it. Private access uses the OAuth 2 device authorization endpoints advertised
by the capability document:

```bash
p2p vertical login wavekit
p2p vertical domain list --registry wavekit --include-private
p2p vertical list --source remote --registry wavekit --include-private
p2p vertical logout wavekit
```

The CLI never accepts a bearer token argument. Access and refresh tokens are
sent only in authorization or OAuth form fields and are omitted from JSON,
configuration, cache metadata and errors.

## Discovery CLI And MCP

```bash
p2p vertical domain list --registry wavekit
p2p vertical domain search software --registry wavekit
p2p vertical domain inspect dom-software --registry wavekit
p2p vertical list --source remote --registry wavekit --domain dom-software
p2p vertical search software --registry wavekit --domain dom-software
```

MCP exposes matching read-only remote network tools:
`p2p_vertical_domain_list`, `p2p_vertical_domain_search`,
`p2p_vertical_domain_inspect`, `p2p_vertical_release_list` and
`p2p_vertical_release_search`. These tools read metadata only. They do not log
in, pull artifacts, write the user cache, initialize projects or apply
governed structure changes.

## Publication

Registries that accept vertical publication advertise a `publish` endpoint.
The client sends one authenticated `multipart/form-data` request containing a
versioned release metadata document and the exact `.p2pv` artifact. The caller
must supply an idempotency key. A successful provider response is:

```yaml
vertical_publication:
  protocol_version: p2p-vertical-registry/v2
  receipt:
    receipt_id: PUB-001
    status: published
    coordinate: example/software-blue@1.0.0
    artifact_checksum: abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
    visibility: public
```

Valid statuses are `published`, `already_present` and `pending_review`.
Coordinate and artifact checksum must match the submitted release exactly.
Publication is available through `p2p vertical draft publish`; see
[VERTICAL-DRAFTS.md](VERTICAL-DRAFTS.md).

## Pull And Cache

```bash
p2p vertical search software --registry wavekit
p2p vertical pull example/software-blue@1.0.0 --registry wavekit
```

Pull resolves exact dependency metadata first. It then downloads every missing
artifact with connection/read timeouts and byte limits into a transaction
directory on the cache filesystem. Before commit it verifies:

- coordinate and portable schema version;
- declared artifact size and SHA-256;
- effective semantic checksum;
- exact dependency coordinates and semantic checksums;
- canonical portable archive safety rules.

The complete closure is installed in a temporary workspace for validation.
Only a fully valid closure is moved into cache paths. A matching repeated pull
returns `already_present`; changed immutable identity returns
`P2P_REGISTRY_IMMUTABILITY_VIOLATION`.

## Initialization

Initialization is offline by default:

```bash
p2p init "My Project" --vertical example/software-blue@1.0.0
```

That command resolves bundled or cached exact coordinates and makes no network
request. Explicitly authorize a missing remote pull with:

```bash
p2p init "My Project" \
  --vertical example/software-blue@1.0.0 \
  --pull --registry wavekit
```

Cached dependencies are installed before their dependent pack through the
existing portable-pack lifecycle. `--vertical-pack PATH` remains the offline
single-artifact input and is mutually exclusive with `--pull` and `--registry`.

## Integration Boundary

Any provider may implement this HTTP protocol, but no provider route, model or
authorization policy is built into P2P Engine. Catalog domains are separate
from project domains. Vertical release metadata is separate from the detached
project-owned structure. Protocol v1 capability documents are unsupported by
the 0.5 current runtime and must be refreshed against a v2 provider.
