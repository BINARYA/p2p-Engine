# Vertical Registry Protocol V1

P2P Engine can discover and pull exact portable vertical releases from a
provider-neutral HTTP registry. Remote access ends at a verified immutable
user cache. Project mutation still uses the standard portable-pack install and
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

Registry configuration contains no bearer or refresh tokens. Login uses the
operating-system credential provider through Python `keyring`; failure to find
a secure backend is reported without a plaintext fallback.

## Capability Document

The client reads this fixed path relative to the configured origin:

```text
/.well-known/p2p-vertical-registry
```

Example response:

```yaml
vertical_registry:
  protocol_version: p2p-vertical-registry/v1
  api_base: /api/vertical-registry/v1
  max_artifact_bytes: 8388608
  endpoints:
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

All advertised URLs must remain on the configured registry origin. HTTPS is
mandatory, except for `localhost`, `127.0.0.1`, and `::1` development
registries explicitly configured with HTTP.

## Release Documents

List and search return:

```yaml
vertical_releases:
  protocol_version: p2p-vertical-registry/v1
  items: []
```

An exact release endpoint returns:

```yaml
vertical_release:
  protocol_version: p2p-vertical-registry/v1
  release:
    coordinate: example/software-blue@1.0.0
    name: Software Blue
    description: Example vertical
    visibility: public
    semantic_checksum: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
    schema_version: 2
    artifact:
      url: /artifacts/example/software-blue/1.0.0/package.p2pv
      sha256: abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
      size: 4096
    dependencies:
      - coordinate: example/software-base@1.0.0
        semantic_checksum: fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
```

Coordinates and dependency coordinates are exact; tags, ranges and implicit
latest-version resolution are not part of protocol v1. Artifact URLs can be
relative or same-origin absolute URLs.

## Authentication

Public list, search, metadata and artifact operations work anonymously when
the provider permits them. Private access uses the OAuth 2 device
authorization endpoints advertised by the capability document:

```bash
p2p vertical login wavekit
p2p vertical list --source remote --registry wavekit --include-private
p2p vertical logout wavekit
```

The CLI never accepts a bearer token argument. Access and refresh tokens are
sent only in authorization or OAuth form fields and are omitted from JSON,
configuration, cache metadata and errors.

## Publication

Registries that accept vertical publication advertise a `publish` endpoint.
The client sends one authenticated `multipart/form-data` request containing a
versioned release metadata document and the exact `.p2pv` artifact. The caller
must supply an idempotency key. A successful provider response is:

```yaml
vertical_publication:
  protocol_version: p2p-vertical-registry/v1
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

WaveKit may implement this HTTP provider protocol, but no WaveKit model or URL
is built into P2P Engine. WaveKit's worker can also continue its existing
handoff of a verified local `.p2pv` path plus expected checksum. Registry MCP
tools are intentionally deferred; protocol v1 is currently exposed through
the CLI and reusable Python services only.
